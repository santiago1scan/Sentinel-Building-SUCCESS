from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.core.backend_contract import telemetry_endpoint, validate_backend_ack
from app.core.catalog import NODES
from app.core.lora_protocol import ALERT, EVENTS, SENSORS, LoRaFrame
from app.core.time_utils import utc_now
from app.datos.canales.lora_udp import VirtualSX1262
from app.datos.repositorios.sqlite_store import StorageLimitReached, StorageWriteError, SummaryStore
from app.negocio.aggregation import aggregate_for_bridge


class BridgeRadio:
    """Adaptador SX1262. En la Beta usa UDP; físicamente será SPI."""

    def __init__(self, node_code: str, receiver_host: str, receiver_port: int,
                 key: bytes, loss_rate: float = 0.0) -> None:
        self.node_code = node_code
        self.online = True
        self.acks: dict[str, str] = {}
        radio_node = 1 if node_code.endswith("1") else 2
        self.channel = VirtualSX1262(
            radio_node, receiver_host, receiver_port, key, self._on_ack, loss_rate
        )

    def _on_ack(self, message_uid: str, status: str) -> None:
        self.acks[message_uid] = status
        print(f"{self.node_code} | lora_ack={status} uid={message_uid}")

    @staticmethod
    def _alert_values(payload: dict[str, Any]) -> tuple[str, str, int, int]:
        for sensor in payload["bridges"][0]["sensors"]:
            model, data = sensor["sensor_model"], sensor["data"]
            rms = data.get("rms_g", data.get("rms_g__max", data.get("rms_max_g", 0)))
            if model == "ADXL355" and rms >= 0.25:
                return model, "VIBRATION_HIGH", int(rms * 1000), 250
            if model == "AMG8833" and data.get("maximum_c", 0) >= 40:
                return model, "HOTSPOT", int(data["maximum_c"] * 100), 4000
            iaq = data.get("iaq_index", data.get("iaq_index__avg", data.get("iaq_avg", 0)))
            if model == "BME688" and iaq >= 250:
                return model, "AIR_QUALITY", int(iaq), 250
            if model == "INA219" and data.get("battery_low", False):
                voltage = data.get("bus_voltage_v", data.get("bus_voltage_v__min", 0))
                return model, "POWER_LOW", int(voltage * 1000), 11000
        return "ADXL355", "VIBRATION_HIGH", 0, 250

    def send(self, payload: dict[str, Any]) -> bool:
        if not self.online:
            return False
        model, event, value, threshold = self._alert_values(payload)
        frame = LoRaFrame(
            ALERT, payload["message_uid"],
            1 if self.node_code.endswith("1") else 2,
            SENSORS[model], EVENTS[event], int(payload["sequence_number"]),
            int(time.time()), value, threshold, 12000,
        )
        evidence = self.channel.transmit(frame)
        print(
            f"{self.node_code} | lora={evidence['result']} bytes={evidence['bytes']} "
            f"rssi={evidence['rssi_dbm']} snr={evidence['snr_db']}"
        )
        return evidence["result"] == "TRANSMITTED"

    def close(self) -> None:
        self.channel.close()


class BridgeService:
    """Procesa datos recibidos; nunca genera lecturas de sensores."""

    def __init__(self, node_code: str, data_dir: Path, backend_url: str | None,
                 node_token: str, receiver_host: str, receiver_port: int,
                 shared_key: bytes, capacity_gb: float = 128.0,
                 limit_ratio: float = 0.70, loss_rate: float = 0.0) -> None:
        if node_code not in NODES:
            raise ValueError(f"Nodo desconocido: {node_code}")
        self.node_code = node_code
        self.store = SummaryStore(data_dir / f"{node_code.lower()}_summary.db", capacity_gb, limit_ratio)
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.node_token = node_token
        self.radio = BridgeRadio(node_code, receiver_host, receiver_port, shared_key, loss_rate)
        self.network_up = True
        self.online = True
        self.sequence = 0
        self.anomalies: set[str] = set()
        self.last_sync = "startup"
        self.lock = threading.RLock()

    def _send_rest(self, payload: dict[str, Any]) -> tuple[bool, str]:
        if not self.network_up or not self.backend_url:
            return False, "rest_unavailable"
        outgoing = dict(payload)
        outgoing.update(delivery_status="realtime", transport="rest", sent_at=utc_now())
        request = urllib.request.Request(
            telemetry_endpoint(self.backend_url),
            data=json.dumps(outgoing, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Node-Token": self.node_token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8", errors="replace")[:2000]
                return validate_backend_ack(
                    response.status, body, payload["message_uid"],
                    len(payload["bridges"][0]["sensors"]),
                )
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:1000]}"
        except (OSError, urllib.error.URLError) as exc:
            return False, str(exc)

    def _deliver(self, item: dict[str, Any]) -> bool:
        uid, payload = item["message_uid"], dict(item["payload"])
        accepted, detail = self._send_rest(payload)
        if accepted:
            self.store.mark_summary(uid, "sent_rest", detail)
            self.store.log_sync(uid, self.node_code, "rest", "accepted")
            self.last_sync = "rest"
            return True

        if payload.get("priority") == "normal":
            self.store.mark_summary(uid, "pending", f"Backend={detail}")
            self.store.log_sync(uid, self.node_code, "rest", "retry")
            self.last_sync = "pending"
            return False

        # El evento inmediato abre la alerta por LoRa. Los resúmenes periódicos
        # posteriores siguen en SQLite, pero no vuelven a alarmar al brigadista.
        if payload.get("delivery_policy") != "immediate":
            self.store.mark_summary(uid, "pending", f"Backend={detail}; alerta LoRa ya emitida")
            self.last_sync = "pending"
            return False

        if item.get("delivery_status") == "pending_backend":
            self.store.mark_summary(uid, "pending_backend", "LoRa backup already received")
            self.last_sync = "pending_backend"
            return False

        if self.radio.send(payload):
            self.store.mark_summary(uid, "pending_backend", "LoRa alert transmitted")
            self.store.log_sync(uid, self.node_code, "lora", "accepted")
            self.last_sync = "lora_backup"
            return False

        self.store.mark_summary(uid, "pending", f"REST={detail}; LoRa unavailable")
        self.store.log_sync(uid, self.node_code, "lora", "failed")
        self.last_sync = "pending"
        return False

    def replay_pending(self) -> int:
        with self.lock:
            if not self.online:
                return 0
            delivered = 0
            for item in self.store.pending_summaries():
                if not self._deliver(item):
                    break
                delivered += 1
            return delivered

    def ingest(self, events: list[dict[str, Any]], window_seconds: float) -> dict[str, Any]:
        with self.lock:
            if not self.online:
                raise RuntimeError(f"{self.node_code} está apagado")
            if not events:
                raise ValueError("El lote no contiene lecturas")
            if any(event.get("node_code") != self.node_code for event in events):
                raise ValueError("El lote contiene lecturas de otro nodo")

            self.replay_pending()
            self.sequence += 1
            for event in events:
                sensor = event["sensor_type"]
                if event.get("quality") == "simulated_anomaly":
                    self.anomalies.add(sensor)
                elif window_seconds == 0:
                    self.anomalies.discard(sensor)

            aggregate = aggregate_for_bridge(self.node_code, events, window_seconds, self.sequence)
            if window_seconds == 0:
                aggregate["delivery_policy"] = "immediate"
            try:
                self.store.save_summary(aggregate, self.node_code)
                self._deliver({
                    "message_uid": aggregate["message_uid"], "payload": aggregate,
                    "delivery_status": "pending",
                })
            except StorageLimitReached:
                self.last_sync = "storage_limit"
                raise
            except StorageWriteError:
                self.last_sync = "storage_error"
                raise
            return aggregate

    def command(self, action: str, value: bool) -> int:
        if action == "network":
            self.network_up = value
            return self.replay_pending() if value else 0
        if action == "bridge":
            self.online = value
            return self.replay_pending() if value else 0
        if action == "lora":
            self.radio.online = value
            return 0
        raise ValueError(f"Acción no soportada: {action}")

    def status(self) -> dict[str, Any]:
        return {
            "node_code": self.node_code, "online": self.online,
            "network_up": self.network_up, "anomalies": sorted(self.anomalies),
            "last_sync": self.last_sync, "lora_up": self.radio.online,
            "lora_acks": dict(self.radio.acks), "storage": self.store.status(),
        }

    def close(self) -> None:
        self.radio.close()
        self.store.close()
