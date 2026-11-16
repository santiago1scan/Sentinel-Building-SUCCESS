from __future__ import annotations

from dataclasses import dataclass


BUILDING_CODE = "SB-001"
GATEWAY_UID = "EDGE-GATEWAY-OUTSIDE"


@dataclass(frozen=True)
class SensorProfile:
    sensor_type: str
    model: str
    interface: str
    unit: str
    samples_per_second: float


SENSORS = {
    "accelerometer": SensorProfile("accelerometer", "ADXL355", "SPI", "g", 100.0),
    "thermal_array": SensorProfile("thermal_array", "AMG8833", "I2C", "degC", 1.0),
    "gas_environmental": SensorProfile("gas_environmental", "BME688", "I2C", "mixed", 1.0),
    "power_monitor": SensorProfile("power_monitor", "INA219", "I2C", "mixed", 1.0),
}


NODES = {
    "NODE-FLOOR-1": {
        "zone_code": "ZONE-F1",
        "floor": 1,
        "bridge_name": "Bridge 1 - Floor 1",
    },
    "NODE-FLOOR-2": {
        "zone_code": "ZONE-F2",
        "floor": 2,
        "bridge_name": "Bridge 2 - Floor 2",
    },
}


def sensor_id(node_code: str, sensor_type: str) -> str:
    return f"{SENSORS[sensor_type].model}-{node_code}"

