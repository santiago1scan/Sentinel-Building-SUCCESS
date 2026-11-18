from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import GATEWAY_UID
from .sensors import utc_now
from .storage import LocalStore


def expand_lora_payload(compact: dict[str, Any]) -> dict[str, Any]:
    bridge = compact["bridge"]
    node_code = bridge["node_code"]
    measurement_types = {
        "ADXL355": "motion",
        "GRID-EYE": "temperature",
        "BME688": "air_quality",
        "INA219": "electrical",
    }
    sensor_list = []
    for sensor in bridge["sensors"]:
        model = sensor["sensor_code"].split("-", 1)[0]
        sensor_list.append({
            "sensor_code": sensor["sensor_code"],
            "sensor_model": model,
            "measurement_type": measurement_types.get(model, "unknown"),
            "sample_count": sensor["sample_count"],
            "data": sensor["data"],
        })
    return {
        "schema_version": "2.0",
        "message_uid": compact["message_uid"],
        # Los resúmenes por LoRa de versiones anteriores no traían el tipo: se deduce de la prioridad.
        "message_type": compact.get("message_type")
        or ("out_of_range" if compact["priority"] != "normal" else "half_hour_summary"),
        "building_uid": compact["building_code"],
        "building_code": compact["building_code"],
        "gateway_uid": GATEWAY_UID,
        "generated_at": compact["generated_at"],
        "sent_at": None,
        "sequence_number": compact["sequence_number"],
        "priority": compact["priority"],
        "quality": "anomaly" if compact["priority"] != "normal" else "valid",
        "delivery_policy": "immediate" if compact["priority"] != "normal" else "periodic",
        "delivery_status": "gateway_received",
        "transport": "lora",
        "window": {
            "start": compact["generated_at"],
            "end": compact["generated_at"],
            "duration_seconds": 0,
            "sample_count": sum(s["sample_count"] for s in bridge["sensors"]),
        },
        "bridges": [{
            "node_uid": node_code,
            "node_code": node_code,
            "node_name": f"Bridge {bridge['floor']} - Floor {bridge['floor']}",
            "floor": bridge["floor"],
            "zone_uid": bridge["zone_code"],
            "zone_code": bridge["zone_code"],
            "sensors": sensor_list,
        }],
    }


class ExternalGateway:
    """Outside-building gateway receiving one aggregate from each bridge."""

    def __init__(self, data_dir, backend_url: str | None = None, node_tokens: dict[str, str] | None = None):
        self.store = LocalStore(data_dir / "gateway_local.db", 128.0, 0.70)
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.node_tokens = node_tokens or {}
        self.online = True

    def receive_lora(self, payload: dict[str, Any]) -> bool:
        payload = expand_lora_payload(payload)
        payload["transport"] = "lora"
        payload["delivery_status"] = "gateway_received"
        inserted = self.store.receive_gateway_message(payload, utc_now())
        if inserted:
            print(
                f"gateway | received node={payload['bridges'][0]['node_code']} "
                f"uid={payload['message_uid']} priority={payload['priority']}"
            )
            self.forward_pending()
        return True

    def forward_pending(self) -> int:
        if not self.online or not self.backend_url:
            return 0
        sent = 0
        for item in self.store.pending_gateway_messages():
            payload = item["payload"]
            node_code = item["node_code"]
            payload["gateway_uid"] = GATEWAY_UID
            payload["delivery_status"] = "realtime"
            payload["transport"] = "rest"
            payload["sent_at"] = utc_now()
            request = urllib.request.Request(
                f"{self.backend_url}/telemetry/aggregate",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Node-Token": self.node_tokens.get(node_code, ""),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    body = response.read().decode("utf-8")
                    if 200 <= response.status < 300:
                        self.store.mark_gateway_message(item["message_uid"], "sent")
                        sent += 1
                        continue
                    self.store.mark_gateway_message(item["message_uid"], "pending")
            except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
                self.store.mark_gateway_message(item["message_uid"], "pending")
        return sent

    def status(self) -> dict[str, Any]:
        result = self.store.status()
        result.update({"gateway_uid": GATEWAY_UID, "online": self.online})
        return result

    def close(self) -> None:
        self.store.close()

