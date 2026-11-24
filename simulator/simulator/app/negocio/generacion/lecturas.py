"""Valores de cada sensor, normales o en anomalía.

Mismo orden de llamadas al generador aleatorio que el simulador original, para
poder repetir resultados con una semilla.
"""

import random
from typing import Any, Callable


# Modo de un sensor: None = normal; "fire" = la anomalía de siempre (incendio, sismo, corte); "candle", "spray" y
# "faulty" = escenarios normales (24-nov-2026). Los valores normales quedan dentro de los rangos de la semilla
# c3f8a2d6b9e1 de monolito-escucha: fuera de ellos, cualquier incidencia arrastraba alertas de energía y movimiento.


def acelerometro(rng: random.Random, modo: str | None) -> dict[str, Any]:
    anomalia = modo is not None
    return {
        "x_g": round(rng.uniform(-0.008, 0.008) if not anomalia else rng.uniform(-0.7, 0.7), 4),
        "y_g": round(rng.uniform(-0.008, 0.008) if not anomalia else rng.uniform(-0.7, 0.7), 4),
        "z_g": round(rng.uniform(0.992, 1.008) if not anomalia else rng.uniform(0.6, 1.6), 4),
        "rms_g": round(rng.uniform(0.001, 0.006) if not anomalia else rng.uniform(0.25, 0.8), 4),
        "frequency_hz": round(rng.uniform(3.2, 3.8) if not anomalia else rng.uniform(1, 8), 2),
    }


def termico(rng: random.Random, modo: str | None) -> dict[str, Any]:
    matriz = [[round(rng.uniform(23.5, 25.0), 2) for _ in range(8)] for _ in range(8)]
    if modo == "candle":
        # Una llama pequeña: 1 o 2 píxeles calientes; el promedio de la cámara casi no cambia.
        for fila, col in ((3, 3), (3, 4))[:rng.randint(1, 2)]:
            matriz[fila][col] = round(rng.uniform(40, 55), 2)
    elif modo is not None:
        for fila, col in ((3, 3), (3, 4), (4, 3), (4, 4)):
            matriz[fila][col] = round(rng.uniform(45, 60), 2)
    return {
        "matrix_size": "8x8",
        "pixels_c": matriz,
        "maximum_c": max(max(fila) for fila in matriz),
        "average_c": round(sum(sum(fila) for fila in matriz) / 64, 2),
        "hot_pixels": sum(valor >= 40 for fila in matriz for valor in fila),
    }


def gas_ambiental(rng: random.Random, modo: str | None) -> dict[str, Any]:
    incendio = modo is not None and modo not in ("spray", "faulty")
    lectura = {
        "temperature_c": round(rng.uniform(22, 27) if not incendio else rng.uniform(30, 42), 2),
        "humidity_percent": round(rng.uniform(75, 90) if not incendio else rng.uniform(70, 90), 2),
        "pressure_hpa": round(rng.uniform(820, 830), 2),
        "iaq_index": rng.randint(55, 95) if not incendio else rng.randint(250, 500),
        "tvoc_ppb": rng.randint(100, 450) if not incendio else rng.randint(900, 3000),
    }
    if modo == "spray":
        # Limpiador o perfume: compuestos volátiles en el aire, sin calor.
        lectura["iaq_index"] = rng.randint(150, 250)
        lectura["tvoc_ppb"] = rng.randint(800, 2000)
    elif modo == "faulty":
        # Sensor dañado: la temperatura salta a un valor que el BME688 no puede medir (rango físico -40…85 °C).
        lectura["temperature_c"] = rng.choice((120.0, -60.0))
    return lectura


def energia(rng: random.Random, modo: str | None) -> dict[str, Any]:
    anomalia = modo is not None
    voltaje = rng.uniform(11.2, 11.9) if not anomalia else rng.uniform(10.2, 11.0)
    corriente = rng.uniform(350, 480) if not anomalia else rng.uniform(900, 1500)
    return {
        "bus_voltage_v": round(voltaje, 3),
        "current_ma": round(corriente, 2),
        "power_mw": round(voltaje * corriente, 2),
        "power_source": "main" if not anomalia else "battery",
        "battery_low": voltaje < 11,
    }


GENERADORES: dict[str, Callable[[random.Random, str | None], dict[str, Any]]] = {
    "accelerometer": acelerometro,
    "thermal_array": termico,
    "gas_environmental": gas_ambiental,
    "power_monitor": energia,
}
