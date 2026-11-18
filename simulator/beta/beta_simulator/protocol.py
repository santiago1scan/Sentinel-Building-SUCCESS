from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any

from .config import BUILDING_CODE, GATEWAY_UID, NODES, SENSORS, sensor_id
from .sensors import utc_now


def _avg(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _summary(values: list[float], name: str) -> dict[str, float]:
    """avg/max/min de una variable con las llaves `<variable>__avg|max|min` que espera el backend."""
    return {
        f"{name}__avg": _avg(values),
        f"{name}__max": round(max(values), 6),
        f"{name}__min": round(min(values), 6),
    }


# Variables de cada sensor: los códigos son los de sensor_metric en el backend.
_VARIABLES = {
    "accelerometer": ("x_g", "y_g", "z_g", "rms_g", "frequency_hz"),
    "thermal_array": ("average_c", "maximum_c", "hot_pixels"),
    "gas_environmental": ("temperature_c", "humidity_percent", "pressure_hpa", "iaq_index", "tvoc_ppb"),
    "power_monitor": ("bus_voltage_v", "current_ma", "power_mw"),
}


def _sensor_data(sensor_type: str, events: list[dict[str, Any]], immediate: bool) -> dict[str, Any]:
    payloads = [event["payload"] for event in events]
    if immediate:
        # Incidente (out_of_range): cada llave es la variable y el valor es el crudo.
        return dict(payloads[-1])
    data: dict[str, Any] = {}
    for name in _VARIABLES[sensor_type]:
        data.update(_summary([float(p[name]) for p in payloads], name))
    if sensor_type == "power_monitor":
        data["battery_low"] = any(bool(p["battery_low"]) for p in payloads)
    return data


def aggregate_for_bridge(
    node_code: str, events: list[dict[str, Any]], window_seconds: float, sequence: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["sensor_type"]].append(event)
    priorities = {event["priority"] for event in events}
    priority = "critical" if "critical" in priorities else "high" if "high" in priorities else "normal"
    sensors = []
    for sensor_type, grouped_events in grouped.items():
        sensors.append({
            "sensor_uid": sensor_id(node_code, sensor_type),
            "sensor_code": sensor_id(node_code, sensor_type),
            "sensor_model": SENSORS[sensor_type].model,
            "measurement_type": {
                "accelerometer": "motion",
                "thermal_array": "temperature",
                "gas_environmental": "air_quality",
                "power_monitor": "electrical",
            }[sensor_type],
            "source_sensor_type": sensor_type,
            "sample_count": len(grouped_events),
            "data": _sensor_data(sensor_type, grouped_events, window_seconds == 0),
        })
    timestamps = [event["generated_at"] for event in events]
    return {
        "schema_version": "2.0",
        "message_uid": str(uuid.uuid4()),
        "message_type": "out_of_range" if window_seconds == 0 else "half_hour_summary",
        "building_uid": BUILDING_CODE,
        "building_code": BUILDING_CODE,
        "gateway_uid": GATEWAY_UID,
        "generated_at": utc_now(),
        "sent_at": None,
        "sequence_number": sequence,
        "priority": priority,
        "quality": "anomaly" if priority != "normal" else "valid",
        "delivery_policy": "immediate" if priority != "normal" else "periodic",
        "delivery_status": "pending",
        "transport": "pending",
        "window": {
            "start": min(timestamps) if timestamps else utc_now(),
            "end": max(timestamps) if timestamps else utc_now(),
            "duration_seconds": window_seconds,
            "sample_count": len(events),
        },
        "bridges": [{
            "node_uid": node_code,
            "node_code": node_code,
            "node_name": NODES[node_code]["bridge_name"],
            "floor": NODES[node_code]["floor"],
            "zone_uid": NODES[node_code]["zone_code"],
            "zone_code": NODES[node_code]["zone_code"],
            "sensors": sensors,
        }],
    }

