from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any

from app.core.catalog import BUILDING_CODE, GATEWAY_UID, NODES, SENSORS, sensor_id
from app.core.time_utils import utc_now


def _avg(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _summary(values: list[float], name: str) -> dict[str, float]:
    return {
        f"{name}__avg": _avg(values),
        f"{name}__max": round(max(values), 6),
        f"{name}__min": round(min(values), 6),
    }


def _sensor_data(
    sensor_type: str,
    events: list[dict[str, Any]],
    immediate: bool,
) -> dict[str, Any]:
    payloads = [event["payload"] for event in events]
    if immediate:
        return dict(payloads[-1])
    if sensor_type == "accelerometer":
        data: dict[str, Any] = {}
        for name in ("x_g", "y_g", "z_g", "rms_g", "frequency_hz"):
            data.update(_summary([float(p[name]) for p in payloads], name))
        return data
    if sensor_type == "thermal_array":
        data = {}
        for name in ("average_c", "maximum_c", "hot_pixels"):
            data.update(_summary([float(p[name]) for p in payloads], name))
        return data
    if sensor_type == "gas_environmental":
        data = {}
        for name in ("temperature_c", "humidity_percent", "pressure_hpa", "iaq_index", "tvoc_ppb"):
            data.update(_summary([float(p[name]) for p in payloads], name))
        return data
    data = {}
    for name in ("bus_voltage_v", "current_ma", "power_mw"):
        data.update(_summary([float(p[name]) for p in payloads], name))
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
        "delivery_policy": "immediate" if window_seconds == 0 else "periodic",
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

