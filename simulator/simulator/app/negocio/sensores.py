"""Sensores que simula cada nodo. Describen el hardware simulado, no la ubicación."""

TIPOS_SENSOR = ("accelerometer", "thermal_array", "gas_environmental", "power_monitor")

SENSORES = {
    "accelerometer": {"model": "ADXL355", "interface": "SPI", "unit": "g"},
    "thermal_array": {"model": "AMG8833", "interface": "I2C", "unit": "degC"},
    "gas_environmental": {"model": "BME688", "interface": "I2C", "unit": "mixed"},
    "power_monitor": {"model": "INA219", "interface": "I2C", "unit": "mixed"},
}

PREFIJO_SENSOR = {
    "accelerometer": "ADXL355",
    "thermal_array": "GRID-EYE",
    "gas_environmental": "BME688",
    "power_monitor": "INA219",
}

# Nombres cortos que usa el panel para referirse a cada sensor.
ALIAS_SENSOR = {
    "adxl355": "accelerometer",
    "grideye": "thermal_array",
    "bme688": "gas_environmental",
    "ina219": "power_monitor",
}

# Prioridad de la lectura cuando el sensor está en anomalía.
PRIORIDAD_ANOMALIA = {
    "accelerometer": "critical",
    "thermal_array": "high",
    "gas_environmental": "high",
    "power_monitor": "critical",
}


def sensor_id(nodo: str, tipo: str) -> str:
    return f"{PREFIJO_SENSOR[tipo]}-{nodo}"


def resolver_sensor(valor: str) -> str:
    """Acepta el alias del panel (adxl355) o el tipo (accelerometer). Devuelve el tipo."""
    texto = valor.strip().lower()
    if texto in ALIAS_SENSOR:
        return ALIAS_SENSOR[texto]
    if texto in TIPOS_SENSOR:
        return texto
    raise ValueError(f"Sensor no reconocido: {valor}")
