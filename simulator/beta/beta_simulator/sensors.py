from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import BUILDING_CODE, NODES, SENSORS, sensor_id


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SensorSimulator:
    """Generates raw-looking readings with configurable anomaly injection."""

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)

    def generate_window(
        self, node_code: str, sequence: int, window_seconds: float,
        anomalies: set[str],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for sensor_type, profile in SENSORS.items():
            count = max(1, round(profile.samples_per_second * window_seconds))
            for sample in range(count):
                events.append(self._event(node_code, sensor_type, sequence, sample, anomalies))
        return events

    def generate_immediate_alert(
        self, node_code: str, sequence: int, sensor_type: str,
    ) -> dict[str, Any]:
        """Generate one abnormal raw reading without waiting for an aggregate window."""
        if sensor_type not in SENSORS:
            raise ValueError(f"Unknown sensor type: {sensor_type}")
        return self._event(
            node_code=node_code,
            sensor_type=sensor_type,
            sequence=sequence,
            sample=0,
            anomalies={sensor_type},
        )

    def generate_immediate_normal(
        self, node_code: str, sequence: int, sensor_type: str,
    ) -> dict[str, Any]:
        """Generate one normal reading to clear an injected alert immediately."""
        if sensor_type not in SENSORS:
            raise ValueError(f"Unknown sensor type: {sensor_type}")
        return self._event(
            node_code=node_code,
            sensor_type=sensor_type,
            sequence=sequence,
            sample=0,
            anomalies=set(),
        )

    def _event(
        self, node_code: str, sensor_type: str, sequence: int,
        sample: int, anomalies: set[str],
    ) -> dict[str, Any]:
        abnormal = sensor_type in anomalies
        if sensor_type == "accelerometer":
            payload = {
                "x_g": round(self.random.uniform(-0.02, 0.02) if not abnormal else self.random.uniform(-0.7, 0.7), 4),
                "y_g": round(self.random.uniform(-0.02, 0.02) if not abnormal else self.random.uniform(-0.7, 0.7), 4),
                "z_g": round(self.random.uniform(0.98, 1.02) if not abnormal else self.random.uniform(0.6, 1.6), 4),
                "rms_g": round(self.random.uniform(0.001, 0.01) if not abnormal else self.random.uniform(0.25, 0.8), 4),
                "frequency_hz": round(self.random.uniform(0.1, 1.0) if not abnormal else self.random.uniform(1, 8), 2),
            }
        elif sensor_type == "thermal_array":
            matrix = [[round(self.random.uniform(23.5, 27.0), 2) for _ in range(8)] for _ in range(8)]
            if abnormal:
                for row, column in ((3, 3), (3, 4), (4, 3), (4, 4)):
                    matrix[row][column] = round(self.random.uniform(45, 60), 2)
            payload = {
                "matrix_size": "8x8",
                "pixels_c": matrix,
                "maximum_c": max(max(row) for row in matrix),
                "average_c": round(sum(sum(row) for row in matrix) / 64, 2),
                "hot_pixels": sum(value >= 40 for row in matrix for value in row),
            }
        elif sensor_type == "gas_environmental":
            payload = {
                "temperature_c": round(self.random.uniform(22, 27) if not abnormal else self.random.uniform(30, 42), 2),
                "humidity_percent": round(self.random.uniform(45, 65) if not abnormal else self.random.uniform(70, 90), 2),
                "pressure_hpa": round(self.random.uniform(995, 1020), 2),
                "iaq_index": self.random.randint(20, 120) if not abnormal else self.random.randint(250, 500),
                "tvoc_ppb": self.random.randint(50, 350) if not abnormal else self.random.randint(900, 3000),
            }
        else:
            voltage = self.random.uniform(11.8, 12.6) if not abnormal else self.random.uniform(10.2, 11.0)
            current = self.random.uniform(650, 1000) if not abnormal else self.random.uniform(900, 1500)
            payload = {
                "bus_voltage_v": round(voltage, 3),
                "current_ma": round(current, 2),
                "power_mw": round(voltage * current, 2),
                "power_source": "main" if not abnormal else "battery",
                "battery_low": voltage < 11,
            }
        return {
            "schema_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "event_type": "sensor_reading",
            "building_code": BUILDING_CODE,
            "node_code": node_code,
            "zone_code": NODES[node_code]["zone_code"],
            "floor": NODES[node_code]["floor"],
            "sensor_code": sensor_id(node_code, sensor_type),
            "sensor_type": sensor_type,
            "sensor_model": SENSORS[sensor_type].model,
            "interface": SENSORS[sensor_type].interface,
            "generated_at": utc_now(),
            "sequence_number": sequence * 100000 + sample,
            "priority": "critical" if sensor_type in {"accelerometer", "power_monitor"} and abnormal else "high" if abnormal else "normal",
            "quality": "simulated_anomaly" if abnormal else "valid",
            "payload": payload,
        }

