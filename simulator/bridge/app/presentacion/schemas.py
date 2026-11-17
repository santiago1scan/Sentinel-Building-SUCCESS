"""Entrada y salida de la API.

La entrada se pasa al servicio sin validar campo por campo: el bridge original
decide qué rechazar (y cuándo) según el flujo que ejecuta. Aquí solo se valida
la forma del cuerpo, igual que bridge_service.py.
"""

from typing import Any

from pydantic import BaseModel, Field


def extraer_lecturas(body: Any) -> list[dict[str, Any]]:
    """Acepta una lista directa o {"readings": [...]}. Lanza ValueError si no es lista."""
    bruto = body["readings"] if isinstance(body, dict) else body
    if not isinstance(bruto, list):
        raise ValueError("readings debe ser una lista")
    return bruto


class AlmacenamientoOut(BaseModel):
    raw_readings: int
    pending: int
    sent: int


class HealthOut(BaseModel):
    status: str
    component: str
    nodes: list[str]
    mqtt_connected: dict[str, bool]
    storage: AlmacenamientoOut


class IngestOut(BaseModel):
    accepted: bool
    raw_inserted: int
    nodes: int
    rest_realtime: int
    mqtt_catch_up: int
    lora_summary: int
    storage: AlmacenamientoOut


class RegistroIn(BaseModel):
    """Datos que pide consulta para registrar el nodo. El código lo fija el bridge, no el navegador."""

    name: str = Field(min_length=1, max_length=150)
    building_id: int = Field(gt=0)
    zone_id: int = Field(gt=0)
