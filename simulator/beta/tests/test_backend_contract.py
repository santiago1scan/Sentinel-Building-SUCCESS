"""El resumen de Beta debe usar los códigos de métrica del catálogo del backend.

Si no coinciden, escucha crea métricas nuevas sin nombre, unidad ni rango por cada llave distinta
(el panel mostraba ~20 métricas sin nombre) y no evalúa alertas.
"""
from __future__ import annotations

import unittest

import json

from beta_simulator.bridge import compact_for_lora
from beta_simulator.config import NODES
from beta_simulator.gateway import expand_lora_payload
from simulator_v2.config import LORA_MAX_PAYLOAD_BYTES
from beta_simulator.protocol import aggregate_for_bridge
from beta_simulator.sensors import SensorSimulator

# metric_code del catálogo sembrado en el backend (migración c3f8a2d6b9e1), por sensor.
CATALOG = {
    "ADXL355": {"x_g", "y_g", "z_g", "rms_g", "frequency_hz"},
    "AMG8833": {"maximum_c", "average_c", "hot_pixels"},
    "BME688": {"temperature_c", "humidity_percent", "pressure_hpa", "iaq_index", "tvoc_ppb"},
    "INA219": {"bus_voltage_v", "current_ma", "power_mw", "power_source", "battery_low"},
}
AGGREGATIONS = ("avg", "max", "min")


def split(key: str) -> tuple[str, str]:
    """Misma regla que escucha (app/analytics/metrics.py)."""
    base, sep, suffix = key.rpartition("__")
    return (base, suffix) if sep and base and suffix in AGGREGATIONS else (key, "raw")


def numeric_codes(data: dict) -> set[str]:
    return {split(key)[0] for key, value in data.items() if isinstance(value, (int, float))}


class BackendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulator = SensorSimulator(seed=42)
        self.node = next(iter(NODES))

    def test_window_summary_uses_catalog_metrics_with_aggregations(self) -> None:
        events = self.simulator.generate_window(self.node, 1, 30.0, set())
        message = aggregate_for_bridge(self.node, events, 30.0, 1)
        self.assertEqual(message["message_type"], "half_hour_summary")
        sensors = message["bridges"][0]["sensors"]
        self.assertEqual(len(sensors), 4)
        for sensor in sensors:
            data = sensor["data"]
            self.assertLessEqual(numeric_codes(data), CATALOG[sensor["sensor_model"]], sensor["sensor_code"])
            for key, value in data.items():
                if isinstance(value, bool):
                    self.assertEqual(key, "battery_low")  # los booleanos viajan sin sufijo
                elif isinstance(value, (int, float)):
                    self.assertIn(split(key)[1], AGGREGATIONS, key)

    def test_each_summary_variable_carries_avg_max_and_min(self) -> None:
        events = self.simulator.generate_window(self.node, 1, 30.0, set())
        sensor = aggregate_for_bridge(self.node, events, 30.0, 1)["bridges"][0]["sensors"][2]
        self.assertEqual(sensor["sensor_model"], "BME688")
        for code in CATALOG["BME688"]:
            for aggregation in AGGREGATIONS:
                self.assertIn(f"{code}__{aggregation}", sensor["data"])

    def test_incident_is_out_of_range_with_raw_catalog_variables(self) -> None:
        event = self.simulator.generate_immediate_alert(self.node, 1, "thermal_array")
        message = aggregate_for_bridge(self.node, [event], 0.0, 1)
        self.assertEqual(message["message_type"], "out_of_range")
        data = message["bridges"][0]["sensors"][0]["data"]
        self.assertLessEqual(numeric_codes(data), CATALOG["AMG8833"])
        self.assertTrue(all(split(key)[1] == "raw" for key in data))

    def test_lora_copy_of_a_summary_fits_and_keeps_its_type(self) -> None:
        events = self.simulator.generate_window(self.node, 1, 30.0, set())
        message = aggregate_for_bridge(self.node, events, 30.0, 1)
        compact = compact_for_lora(message)
        size = len(json.dumps(compact, separators=(",", ":")).encode("utf-8"))
        self.assertLessEqual(size, LORA_MAX_PAYLOAD_BYTES)
        expanded = expand_lora_payload(compact)
        self.assertEqual(expanded["message_type"], "half_hour_summary")
        for sensor in expanded["bridges"][0]["sensors"]:
            self.assertFalse([k for k in sensor["data"] if k.endswith(("__max", "__min"))])
            self.assertLessEqual(numeric_codes(sensor["data"]), CATALOG[sensor["sensor_model"]])


if __name__ == "__main__":
    unittest.main()
