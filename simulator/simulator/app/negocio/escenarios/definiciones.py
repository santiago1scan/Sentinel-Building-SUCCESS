"""Escenarios de desastre: qué sensores se alteran. Mismas definiciones del panel original."""

from typing import Any

# "mode": cómo se altera cada sensor (app/negocio/generacion/lecturas.py). "fire" es la anomalía de siempre.
# Escenarios normales (24-nov-2026): vela, limpiador o perfume, sensor dañado. El simulador no dice si son graves:
# eso lo decide el backend (monolito-escucha, app/analytics/severity.py).
ESCENARIOS: dict[str, dict[str, Any]] = {
    "fire": {"label": "Fire", "sensors": ("grideye", "bme688"), "mode": "fire", "todos_los_nodos": True},
    "earthquake": {"label": "Earthquake", "sensors": ("adxl355",), "mode": "fire", "todos_los_nodos": True},
    # La falla de energía y el sensor dañado exigen elegir exactamente un nodo.
    "power_failure": {"label": "Power failure", "sensors": ("ina219",), "mode": "fire", "todos_los_nodos": False},
    "candle": {"label": "Candle", "sensors": ("grideye",), "mode": "candle", "todos_los_nodos": True},
    "spray": {"label": "Cleaner or perfume spray", "sensors": ("bme688",), "mode": "spray",
              "todos_los_nodos": True},
    "faulty_sensor": {"label": "Faulty sensor", "sensors": ("bme688",), "mode": "faulty",
                      "todos_los_nodos": False},
}

# Escenarios que se aplican a un único nodo.
UN_SOLO_NODO = {"power_failure", "faulty_sensor"}


def nodos_por_defecto(nombre: str, nodos_simulados: list[str]) -> list[str]:
    return list(nodos_simulados) if ESCENARIOS[nombre]["todos_los_nodos"] else []
