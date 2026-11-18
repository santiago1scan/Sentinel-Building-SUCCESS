from __future__ import annotations

import json
import random
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from beta_simulator.bridge import compact_for_lora
from beta_simulator.config import NODES
from beta_simulator.protocol import aggregate_for_bridge
from beta_simulator.sensors import SensorSimulator, utc_now

from .backend_contract import telemetry_endpoint, validate_backend_ack
from .config import LORA_MAX_PAYLOAD_BYTES
from .gateway import ExternalReceiver
from .storage import StorageLimitReached, StorageWriteError, SummaryStore


class SimulatedRadio:
    def __init__(self, receiver: ExternalReceiver, loss_rate: float = 0.0) -> None:
        self.receiver = receiver
        self.loss_rate = loss_rate
        self.online = {node: True for node in NODES}

    def send(self, node_code: str, payload: dict[str, Any]) -> bool:
        if not self.online.get(node_code, False):
            return False
        compact = compact_for_lora(payload)
        encoded = json.dumps(compact, separators=(",", ":")).encode("utf-8")
        if len(encoded) > LORA_MAX_PAYLOAD_BYTES:
            print(f"lora | payload_too_large node={node_code} bytes={len(encoded)}")
            return False
        if random.random() < self.loss_rate:
            print(f"lora | packet_lost node={node_code}")
            return False
        return self.receiver.receive_lora(compact)


class PhysicalBetaBridge:
    """One independent physical bridge/node in the beta simulator."""

    def __init__(
        self,
        node_code: str,
        data_dir: Path,
        receiver: ExternalReceiver,
        radio: SimulatedRadio,
        sensor_simulator: SensorSimulator,
        backend_url: str | None = None,
        node_token: str | None = None,
        capacity_gb: float = 128.0,
        limit_ratio: float = 0.70,
    ) -> None:
        self.node_code = node_code
        self.store = SummaryStore(data_dir / f"{node_code.lower()}_summary.db", capacity_gb, limit_ratio)
        self.receiver = receiver
        self.radio = radio
        self.sensor_simulator = sensor_simulator
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.node_token = node_token
        self.network_up = True
        self.online = True
        self.sequence = 0
        self.anomalies: set[str] = set()
        self.last_sync = "startup"
        self.operation_lock = threading.RLock()

    def _safe_log(self, uid: str, transport: str, result: str) -> None:
        self.store.log_sync(uid, self.node_code, transport, result)

    def _send_rest(self, aggregate: dict[str, Any]) -> tuple[bool, str]:
        if not self.network_up or not self.backend_url:
            return False, "rest_unavailable"
        payload = dict(aggregate)
        payload["delivery_status"] = "realtime"
        payload["transport"] = "rest"
        payload["sent_at"] = utc_now()
        request = urllib.request.Request(
            telemetry_endpoint(self.backend_url),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Node-Token": self.receiver.token_for(self.node_code) or self.node_token or "",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8", errors="replace")[:2000]
                return validate_backend_ack(
                    response.status,
                    body,
                    aggregate["message_uid"],
                    len(aggregate["bridges"][0]["sensors"]),
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:2000]
            return False, f"HTTP {exc.code}: {body}"
        except (OSError, urllib.error.URLError) as exc:
            return False, str(exc)

    def _send_lora(self, aggregate: dict[str, Any]) -> tuple[bool, str]:
        payload = dict(aggregate)
        payload["delivery_status"] = "gateway_received"
        payload["transport"] = "lora"
        return self.radio.send(self.node_code, payload), "gateway_received"

    def _deliver(self, item: dict[str, Any]) -> bool:
        """Try backend delivery first and use LoRa only as a backup copy.

        A LoRa acknowledgement does not remove the summary from the backend
        queue. Only a successful REST response completes delivery.
        """
        uid = item["message_uid"]
        aggregate = dict(item["payload"])
        ok, detail = self._send_rest(aggregate)
        if ok:
            self.store.mark_summary(uid, "sent_rest", detail)
            self._safe_log(uid, "rest", "accepted")
            self.last_sync = "rest"
            return True

        # LoRa is an offline fallback, not a replacement for a reachable
        # Internet path whose backend is disabled or rejecting requests.
        if self.network_up:
            pending_status = (
                "pending_backend"
                if item.get("delivery_status") == "pending_backend"
                else "pending"
            )
            self.store.mark_summary(uid, pending_status, f"Backend={detail}")
            self._safe_log(uid, "rest", "retry")
            self.last_sync = pending_status
            return False

        # The external receiver already has this message. Do not send the same
        # LoRa backup on every cycle; retain it for backend synchronization.
        if item.get("delivery_status") == "pending_backend":
            self.store.mark_summary(
                uid, "pending_backend",
                f"Backend={detail}; LoRa backup already received",
            )
            self._safe_log(uid, "rest", "retry")
            self.last_sync = "pending_backend"
            return False

        lora_ok, lora_detail = self._send_lora(aggregate)
        if lora_ok:
            self.store.mark_summary(uid, "pending_backend", lora_detail)
            self._safe_log(uid, "lora", "accepted")
            self.last_sync = "lora_backup"
            return False

        self.store.mark_summary(uid, "pending", f"REST={detail}; LoRa={lora_detail}")
        self._safe_log(uid, "retry", "pending")
        self.last_sync = "pending"
        return False

    def replay_pending(self) -> int:
        """Replay pending summaries in generated order after recovery."""
        with self.operation_lock:
            if not self.online:
                return 0
            delivered = 0
            for item in self.store.pending_summaries():
                if self._deliver(item):
                    delivered += 1
                else:
                    # Keep chronological order: if the first pending item cannot
                    # be delivered, do not jump over it to send newer items.
                    break
            return delivered

    def _run_immediate_sensor_state(
        self, sensor_type: str, abnormal: bool,
    ) -> dict[str, Any]:
        """Create and route an immediate sensor-state aggregate."""
        with self.operation_lock:
            if not self.online:
                raise RuntimeError(f"{self.node_code} is offline")
            if abnormal:
                self.anomalies.add(sensor_type)
            else:
                self.anomalies.discard(sensor_type)
            self.sequence += 1
            event = (
                self.sensor_simulator.generate_immediate_alert(
                    self.node_code, self.sequence, sensor_type
                )
                if abnormal
                else self.sensor_simulator.generate_immediate_normal(
                    self.node_code, self.sequence, sensor_type
                )
            )
            aggregate = aggregate_for_bridge(
                self.node_code, [event], window_seconds=0.0, sequence=self.sequence
            )
            # Clearing an alert is also operationally important and must not
            # wait for the next periodic window.
            aggregate["delivery_policy"] = "immediate"
            saved = self.store.save_summary(aggregate, self.node_code)
            if saved:
                self._deliver({
                    "message_uid": aggregate["message_uid"],
                    "node_code": self.node_code,
                    "payload": aggregate,
                    "attempts": 0,
                })
            print(
                f"{self.node_code} | immediate_{'alert' if abnormal else 'clear'} "
                f"sensor={sensor_type} "
                f"priority={aggregate['priority']} uid={aggregate['message_uid']} "
                f"last_sync={self.last_sync}"
            )
            return aggregate

    def run_immediate_alert(self, sensor_type: str) -> dict[str, Any]:
        """Create and route a priority aggregate as soon as an anomaly is detected."""
        return self._run_immediate_sensor_state(sensor_type, abnormal=True)

    def run_immediate_clear(self, sensor_type: str) -> dict[str, Any]:
        """Publish recovery immediately instead of waiting for the periodic window."""
        return self._run_immediate_sensor_state(sensor_type, abnormal=False)

    def run_window(self, window_seconds: float) -> dict[str, Any]:
        with self.operation_lock:
            # Recovery is handled before generating the next window, so queued
            # events are replayed in chronological order as soon as possible.
            self.replay_pending()
            self.sequence += 1
            raw_events = self.sensor_simulator.generate_window(
                self.node_code, self.sequence, window_seconds, self.anomalies
            )
            aggregate = aggregate_for_bridge(self.node_code, raw_events, window_seconds, self.sequence)
            saved = False
            try:
                saved = self.store.save_summary(aggregate, self.node_code)
                self._deliver({
                    "message_uid": aggregate["message_uid"],
                    "node_code": self.node_code,
                    "payload": aggregate,
                    "attempts": 0,
                })
            except StorageLimitReached as exc:
                self._safe_log(aggregate["message_uid"], "storage", "limit_reached")
                self.last_sync = "storage_limit"
                print(f"{self.node_code} | storage_limit | {exc}")
            except StorageWriteError as exc:
                self._safe_log(aggregate["message_uid"], "storage", "write_error")
                self.last_sync = "storage_error"
                print(f"{self.node_code} | storage_error | {exc}")

            state = self.store.status()
            print(
                f"{self.node_code} | raw_memory={len(raw_events):04d} "
                f"summary_saved={int(saved):02d} | last_sync={self.last_sync} "
                f"pending={state['pending']} | raw_persisted=00"
            )
            return aggregate

    def status(self) -> dict[str, Any]:
        return {
            "node_code": self.node_code,
            "online": self.online,
            "network_up": self.network_up,
            "anomalies": sorted(self.anomalies),
            "last_sync": self.last_sync,
            "storage": self.store.status(),
        }

    def close(self) -> None:
        self.store.close()
