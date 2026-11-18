from __future__ import annotations

import threading
from typing import Any

from app.core.catalog import NODES
from app.datos.canales.bridge_client import BridgeClient
from app.datos.generadores.virtual_sensors import SensorSimulator


ALIASES = {
    "adxl355": "accelerometer", "amg8833": "thermal_array",
    "grideye": "thermal_array", "bme688": "gas_environmental",
    "ina219": "power_monitor",
}


class SimulatorService:
    """Genera datos; no almacena resúmenes ni decide transportes."""

    def __init__(self, bridge_urls: dict[str, str], window_seconds: float) -> None:
        self.clients = {node: BridgeClient(url) for node, url in bridge_urls.items()}
        self.generator = SensorSimulator(seed=42)
        self.window_seconds = window_seconds
        self.sequence = {node: 0 for node in NODES}
        self.anomalies = {node: set() for node in NODES}
        self.running = True
        self.last_errors: dict[str, str] = {}
        threading.Thread(target=self._loop, daemon=True).start()

    def _send_window(self, node: str) -> None:
        self.sequence[node] += 1
        events = self.generator.generate_window(
            node, self.sequence[node], self.window_seconds, self.anomalies[node]
        )
        self.clients[node].ingest(events, self.window_seconds)
        self.last_errors.pop(node, None)

    def _loop(self) -> None:
        while self.running:
            for node in NODES:
                try:
                    self._send_window(node)
                except (OSError, RuntimeError, ValueError) as exc:
                    self.last_errors[node] = str(exc)
            threading.Event().wait(self.window_seconds)

    def anomaly(self, node: str, sensor: str, active: bool) -> dict[str, Any]:
        normalized = sensor.strip().lower()
        sensor_type = ALIASES.get(normalized, normalized)
        self.sequence[node] += 1
        if active:
            self.anomalies[node].add(sensor_type)
            event = self.generator.generate_immediate_alert(node, self.sequence[node], sensor_type)
        else:
            self.anomalies[node].discard(sensor_type)
            event = self.generator.generate_immediate_normal(node, self.sequence[node], sensor_type)
        return self.clients[node].ingest([event], 0.0)

    def control(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        target = body.get("target")
        clients = [self.clients[target]] if target else list(self.clients.values())
        return [client.control(body) for client in clients]

    def close(self) -> None:
        self.running = False
