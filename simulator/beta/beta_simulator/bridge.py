from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import NODES
from .gateway import ExternalGateway
from .protocol import aggregate_for_bridge
from .sensors import SensorSimulator, utc_now
from .storage import LocalStore


class SimulatedLoRa:
    def __init__(self, gateway: ExternalGateway, max_payload_bytes: int = 1200, loss_rate: float = 0.0):
        self.gateway = gateway
        self.max_payload_bytes = max_payload_bytes
        self.loss_rate = loss_rate
        self.online = {node: True for node in NODES}

    def send(self, node_code: str, payload: dict[str, Any]) -> bool:
        compact = compact_for_lora(payload)
        encoded = json.dumps(compact, separators=(",", ":")).encode("utf-8")
        if not self.online.get(node_code, False):
            return False
        if len(encoded) > self.max_payload_bytes:
            print(f"lora | payload_too_large node={node_code} bytes={len(encoded)}")
            return False
        import random
        if random.random() < self.loss_rate:
            print(f"lora | packet_lost node={node_code}")
            return False
        return self.gateway.receive_lora(compact)


def _lora_data(data: dict[str, Any], message_type: str) -> dict[str, Any]:
    """La trama es pequeña: en un resumen solo viajan los promedios (y los booleanos).

    El resumen completo (avg, max y min) sale por REST cuando vuelve la red; el backend deduplica
    por message_uid.
    """
    if message_type != "half_hour_summary":
        return data
    return {key: value for key, value in data.items()
            if not key.endswith(("__max", "__min"))}


def compact_for_lora(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep LoRa traffic small; the gateway reconstructs the v2 envelope."""
    bridge = payload["bridges"][0]
    return {
        "message_uid": payload["message_uid"],
        "message_type": payload["message_type"],
        "building_code": payload["building_code"],
        "generated_at": payload["generated_at"],
        "sequence_number": payload["sequence_number"],
        "priority": payload["priority"],
        "bridge": {
            "node_code": bridge["node_code"],
            "floor": bridge["floor"],
            "zone_code": bridge["zone_code"],
            "sensors": [
                {
                    "sensor_code": sensor["sensor_code"],
                    "sample_count": sensor["sample_count"],
                    "data": _lora_data(sensor["data"], payload["message_type"]),
                }
                for sensor in bridge["sensors"]
            ],
        },
    }


class SimulatedBridge:
    def __init__(
        self, node_code: str, data_dir: Path, gateway: ExternalGateway,
        radio: SimulatedLoRa, sensor_sim: SensorSimulator,
        backend_url: str | None = None, node_token: str | None = None,
        capacity_gb: float = 128.0, limit_ratio: float = 0.70,
    ):
        self.node_code = node_code
        self.store = LocalStore(data_dir / f"{node_code.lower()}.db", capacity_gb, limit_ratio)
        self.gateway = gateway
        self.radio = radio
        self.sensor_sim = sensor_sim
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.node_token = node_token
        self.online = True
        self.sequence = 0
        self.anomalies: set[str] = set()

    def run_window(self, window_seconds: float) -> dict[str, Any]:
        self.sequence += 1
        events = self.sensor_sim.generate_window(self.node_code, self.sequence, window_seconds, self.anomalies)
        for event in events:
            self.store.save_raw(event)
        aggregate = aggregate_for_bridge(self.node_code, events, window_seconds, self.sequence)
        self.store.save_aggregate(aggregate, self.node_code)
        delivered = self._send_rest(aggregate)
        if not delivered:
            delivered = self._send_lora(aggregate)
        status = "sent" if delivered else "pending"
        self.store.mark_aggregate(aggregate["message_uid"], status, "delivery attempted")
        print(
            f"{self.node_code} | raw={len(events):04d} | "
            f"rest={'ON' if self.backend_url and delivered else 'OFF'} | "
            f"lora={'ACK' if delivered and not self.backend_url else 'standby'} | "
            f"priority={aggregate['priority']} | pending={self.store.status()['pending']}"
        )
        return aggregate

    def _send_rest(self, aggregate: dict[str, Any]) -> bool:
        if not self.online or not self.backend_url:
            return False
        payload = dict(aggregate)
        payload["delivery_status"] = "realtime"
        payload["transport"] = "rest"
        payload["sent_at"] = utc_now()
        request = urllib.request.Request(
            f"{self.backend_url}/telemetry/aggregate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Node-Token": self.node_token or "",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if 200 <= response.status < 300:
                    return True
        except (OSError, urllib.error.HTTPError, urllib.error.URLError):
            return False
        return False

    def _send_lora(self, aggregate: dict[str, Any]) -> bool:
        payload = dict(aggregate)
        payload["delivery_status"] = "gateway_received"
        payload["transport"] = "lora"
        return self.radio.send(self.node_code, payload)

    def status(self) -> dict[str, Any]:
        return {
            "node_code": self.node_code,
            "online": self.online,
            "anomalies": sorted(self.anomalies),
            "storage": self.store.status(),
        }

    def close(self) -> None:
        self.store.close()

