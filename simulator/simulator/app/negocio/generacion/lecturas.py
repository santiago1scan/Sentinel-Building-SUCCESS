"""Valores de cada sensor, normales o en anomalía.

Mismo orden de llamadas al generador aleatorio que el simulador original, para
poder repetir resultados con una semilla.
"""

import random
from typing import Any, Callable


def acelerometro(rng: random.Random, anomalia: bool) -> dict[str, Any]:
    return {
        "x_g": round(rng.uniform(-0.02, 0.02) if not anomalia else rng.uniform(-0.7, 0.7), 4),
        "y_g": round(rng.uniform(-0.02, 0.02) if not anomalia else rng.uniform(-0.7, 0.7), 4),
        "z_g": round(rng.uniform(0.98, 1.02) if not anomalia else rng.uniform(0.6, 1.6), 4),
        "rms_g": round(rng.uniform(0.001, 0.01) if not anomalia else rng.uniform(0.25, 0.8), 4),
        "frequency_hz": round(rng.uniform(0.1, 1.0) if not anomalia else rng.uniform(1, 8), 2),
    }


def termico(rng: random.Random, anomalia: bool) -> dict[str, Any]:
    matriz = [[round(rng.uniform(23.5, 27.0), 2) for _ in range(8)] for _ in range(8)]
    if anomalia:
        for fila, col in ((3, 3), (3, 4), (4, 3), (4, 4)):
            matriz[fila][col] = round(rng.uniform(45, 60), 2)
    return {
        "matrix_size": "8x8",
        "pixels_c": matriz,
        "maximum_c": max(max(fila) for fila in matriz),
        "average_c": round(sum(sum(fila) for fila in matriz) / 64, 2),
        "hot_pixels": sum(valor >= 40 for fila in matriz for valor in fila),
    }


def gas_ambiental(rng: random.Random, anomalia: bool) -> dict[str, Any]:
    return {
        "temperature_c": round(rng.uniform(22, 27) if not anomalia else rng.uniform(30, 42), 2),
        "humidity_percent": round(rng.uniform(45, 65) if not anomalia else rng.uniform(70, 90), 2),
        "pressure_hpa": round(rng.uniform(995, 1020), 2),
        "iaq_index": rng.randint(20, 120) if not anomalia else rng.randint(250, 500),
        "tvoc_ppb": rng.randint(50, 350) if not anomalia else rng.randint(900, 3000),
    }


def energia(rng: random.Random, anomalia: bool) -> dict[str, Any]:
    voltaje = rng.uniform(11.8, 12.6) if not anomalia else rng.uniform(10.2, 11.0)
    corriente = rng.uniform(650, 1000) if not anomalia else rng.uniform(900, 1500)
    return {
        "bus_voltage_v": round(voltaje, 3),
        "current_ma": round(corriente, 2),
        "power_mw": round(voltaje * corriente, 2),
        "power_source": "main" if not anomalia else "battery",
        "battery_low": voltaje < 11,
    }


GENERADORES: dict[str, Callable[[random.Random, bool], dict[str, Any]]] = {
    "accelerometer": acelerometro,
    "thermal_array": termico,
    "gas_environmental": gas_ambiental,
    "power_monitor": energia,
}
