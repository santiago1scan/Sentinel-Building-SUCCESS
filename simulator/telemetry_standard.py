"""Modelo de telemetria estandarizada para Sentinel.

El bridge conserva los eventos originales, pero hacia la caja negra envia
un resumen por ventana. Los UID se derivan de forma estable para que no
cambien al reiniciar el simulador.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import statistics
import uuid
from typing import Any

SCHEMA_VERSION = "1.0"
UID_NAMESPACE = uuid.UUID("f4d8f2d3-0a82-4c5e-9f15-6af5d2e8e0d1")

MEASUREMENT_TYPES = {
    "accelerometer": "motion",
    "thermal_array": "temperature",
    "gas_environmental": "air_quality",
    "power_monitor": "electrical",
}


def stable_uid(kind: str, value: str) -> str:
    return str(uuid.uuid5(UID_NAMESPACE, f"{kind}:{value}"))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _avg(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _sensor_data(sensor_type: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    payloads = [event["payload"] for event in events]
    if sensor_type == "accelerometer":
        return {
            "x_avg_g": _avg([float(p["x_g"]) for p in payloads]),
            "y_avg_g": _avg([float(p["y_g"]) for p in payloads]),
            "z_avg_g": _avg([float(p["z_g"]) for p in payloads]),
            "rms_avg_g": _avg([float(p["rms_g"]) for p in payloads]),
            "rms_max_g": round(max(float(p["rms_g"]) for p in payloads), 6),
            "frequency_avg_hz": _avg([float(p["frequency_hz"]) for p in payloads]),
        }
    if sensor_type == "thermal_array":
        return {
            "average_avg_c": _avg([float(p["average_c"]) for p in payloads]),
            "maximum_avg_c": _avg([float(p["maximum_c"]) for p in payloads]),
            "maximum_c": round(max(float(p["maximum_c"]) for p in payloads), 4),
            "hot_pixels_max": max(int(p["hot_pixels"]) for p in payloads),
            "matrix_size": "8x8",
        }
    if sensor_type == "gas_environmental":
        return {
            "temperature_avg_c": _avg([float(p["temperature_c"]) for p in payloads]),
            "humidity_avg_percent": _avg([float(p["humidity_percent"]) for p in payloads]),
            "pressure_avg_hpa": _avg([float(p["pressure_hpa"]) for p in payloads]),
            "iaq_avg": _avg([float(p["iaq_index"]) for p in payloads]),
            "tvoc_avg_ppb": _avg([float(p["tvoc_ppb"]) for p in payloads]),
        }
    if sensor_type == "power_monitor":
        voltages = [float(p["bus_voltage_v"]) for p in payloads]
        return {
            "voltage_avg_v": _avg(voltages),
            "voltage_min_v": round(min(voltages), 6),
            "voltage_max_v": round(max(voltages), 6),
            "current_avg_ma": _avg([float(p["current_ma"]) for p in payloads]),
            "power_avg_mw": _avg([float(p["power_mw"]) for p in payloads]),
            "battery_low": any(bool(p["battery_low"]) for p in payloads),
        }
    raise ValueError(f"sensor_type no soportado: {sensor_type}")


def aggregate_readings(readings: list[dict[str, Any]], building_id: str,
                       interval_s: float, sequence: int,
                       node_catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Construye el contrato estandarizado enviado a la caja negra."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in readings:
        grouped[(event["node_id"], event["sensor_type"])].append(event)

    bridges: dict[str, dict[str, Any]] = {}
    timestamps = [event["generated_at"] for event in readings]
    for (node_id, sensor_type), events in grouped.items():
        node = node_catalog[node_id]
        bridge = bridges.setdefault(node_id, {
            "node_uid": stable_uid("bridge", f"{building_id}:{node_id}"),
            "node_code": node_id,
            "node_name": node["bridge_name"],
            "floor": node["floor"],
            "zone_uid": stable_uid("zone", f"{building_id}:{node['zone_id']}"),
            "zone_code": node["zone_id"],
            "sensors": [],
        })
        bridge["sensors"].append({
            "sensor_uid": stable_uid("sensor", events[0]["sensor_id"]),
            "sensor_code": events[0]["sensor_id"],
            "sensor_model": events[0]["sensor_model"],
            "measurement_type": MEASUREMENT_TYPES[sensor_type],
            "source_sensor_type": sensor_type,
            "sample_count": len(events),
            "data": _sensor_data(sensor_type, events),
        })

    priorities = {event["priority"] for event in readings}
    priority = "critical" if "critical" in priorities else "high" if "high" in priorities else "normal"
    return {
        "schema_version": SCHEMA_VERSION,
        "message_uid": str(uuid.uuid4()),
        "message_type": "telemetry_aggregate",
        "building_uid": stable_uid("building", building_id),
        "building_code": building_id,
        "generated_at": now_utc(),
        "sequence_number": sequence,
        "priority": priority,
        "quality": "anomaly" if priority != "normal" else "valid",
        "delivery_policy": "immediate" if priority != "normal" else "periodic",
        # Se completan cuando el bridge elige el canal de salida.
        "delivery_status": "pending",
        "transport": "pending",
        "sent_at": None,
        "window": {
            "start": min(timestamps) if timestamps else now_utc(),
            "end": max(timestamps) if timestamps else now_utc(),
            "duration_seconds": interval_s,
            "sample_count": len(readings),
        },
        "bridges": list(bridges.values()),
    }
