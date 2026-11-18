from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any

from app.core.catalog import BUILDING_CODE, GATEWAY_UID, NODES, SENSORS, sensor_id
from app.core.time_utils import utc_now


def _avg(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _sensor_data(sensor_type: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    payloads = [event["payload"] for event in events]
    if sensor_type == "accelerometer":
        return {
            "x_avg_g": _avg([p["x_g"] for p in payloads]),
            "y_avg_g": _avg([p["y_g"] for p in payloads]),
            "z_avg_g": _avg([p["z_g"] for p in payloads]),
            "rms_avg_g": _avg([p["rms_g"] for p in payloads]),
            "rms_max_g": round(max(p["rms_g"] for p in payloads), 6),
            "frequency_avg_hz": _avg([p["frequency_hz"] for p in payloads]),
        }
    if sensor_type == "thermal_array":
        return {
            "average_avg_c": _avg([p["average_c"] for p in payloads]),
            "maximum_avg_c": _avg([p["maximum_c"] for p in payloads]),
            "maximum_c": round(max(p["maximum_c"] for p in payloads), 4),
            "hot_pixels_max": max(p["hot_pixels"] for p in payloads),
            "matrix_size": "8x8",
        }
    if sensor_type == "gas_environmental":
        return {
            "temperature_avg_c": _avg([p["temperature_c"] for p in payloads]),
            "humidity_avg_percent": _avg([p["humidity_percent"] for p in payloads]),
            "pressure_avg_hpa": _avg([p["pressure_hpa"] for p in payloads]),
            "iaq_avg": _avg([p["iaq_index"] for p in payloads]),
            "tvoc_avg_ppb": _avg([p["tvoc_ppb"] for p in payloads]),
        }
    voltage = [p["bus_voltage_v"] for p in payloads]
    return {
        "voltage_avg_v": _avg(voltage),
        "voltage_min_v": round(min(voltage), 6),
        "voltage_max_v": round(max(voltage), 6),
        "current_avg_ma": _avg([p["current_ma"] for p in payloads]),
        "power_avg_mw": _avg([p["power_mw"] for p in payloads]),
        "battery_low": any(p["battery_low"] for p in payloads),
    }


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
            "data": _sensor_data(sensor_type, grouped_events),
        })
    timestamps = [event["generated_at"] for event in events]
    return {
        "schema_version": "2.0",
        "message_uid": str(uuid.uuid4()),
        "message_type": "telemetry_aggregate",
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

