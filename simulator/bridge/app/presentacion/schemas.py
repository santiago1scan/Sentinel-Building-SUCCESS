"""Contratos de entrada y salida de la API.

Los modelos reflejan el payload que envía el simulador y el contrato
estandarizado que recibe la caja negra (telemetry_standard.py).
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Prioridad = Literal["normal", "high", "critical"]
TipoSensor = Literal["accelerometer", "thermal_array", "gas_environmental", "power_monitor"]


class LecturaIn(BaseModel):
    # extra="allow": el bridge conserva el evento original completo en SQLite.
    model_config = ConfigDict(extra="allow")

    event_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    sensor_id: str = Field(min_length=1)
    sensor_type: TipoSensor
    sensor_model: str
    generated_at: str
    priority: Prioridad
    payload: dict[str, Any]


def extraer_lecturas(body: Any) -> list[LecturaIn]:
    """Acepta una lista directa o {"readings": [...]}. Lanza ValueError si no es válido."""
    bruto = body["readings"] if isinstance(body, dict) else body
    if not isinstance(bruto, list):
        raise ValueError("readings debe ser una lista")
    return [LecturaIn.model_validate(item) for item in bruto]


class AgregadoOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    message_uid: str
    message_type: Literal["telemetry_aggregate"]
    building_code: str
    generated_at: str
    sequence_number: int
    priority: Prioridad
    bridges: list[dict[str, Any]]


class AlmacenamientoOut(BaseModel):
    raw_readings: int
    pending: int
    sent: int


class IngestOut(BaseModel):
    accepted: bool
    raw_inserted: int
    nodes: int
    rest_realtime: int
    mqtt_catch_up: int
    lora_summary: int
    storage: AlmacenamientoOut
