"""Escenarios de desastre: qué sensores se alteran. Mismas definiciones del panel original."""

from typing import Any

ESCENARIOS: dict[str, dict[str, Any]] = {
    "fire": {"label": "Fire", "sensors": ("grideye", "bme688"), "todos_los_nodos": True},
    "earthquake": {"label": "Earthquake", "sensors": ("adxl355",), "todos_los_nodos": True},
    # La falla de energía exige elegir exactamente un nodo.
    "power_failure": {"label": "Power failure", "sensors": ("ina219",), "todos_los_nodos": False},
}


def nodos_por_defecto(nombre: str, nodos_simulados: list[str]) -> list[str]:
    return list(nodos_simulados) if ESCENARIOS[nombre]["todos_los_nodos"] else []
