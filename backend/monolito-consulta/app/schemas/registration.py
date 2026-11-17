"""Schemas del registro de nodos por solicitud."""
import datetime

from pydantic import BaseModel, Field, field_validator


class SensorRegistration(BaseModel):
    """Un sensor del nodo que se registra junto con él. El tipo debe existir (sensor_type.sensor_type_id)."""
    code: str = Field(min_length=1, max_length=100)
    sensor_type_id: int = Field(gt=0)


class RegistrationRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    # Ids de la base de datos (building.building_id y zone.zone_id). La zona debe pertenecer al edificio.
    building_id: int = Field(gt=0)
    zone_id: int = Field(gt=0)
    # Sensores del nodo: se crean al aprobar, junto con el nodo.
    sensors: list[SensorRegistration] = Field(default_factory=list, max_length=50)

    @field_validator("sensors")
    @classmethod
    def sensor_codes_are_unique(cls, sensors: list[SensorRegistration]) -> list[SensorRegistration]:
        codes = [sensor.code for sensor in sensors]
        if len(codes) != len(set(codes)):
            raise ValueError("Los códigos de sensor no pueden repetirse")
        return sensors


class RegistrationAccepted(BaseModel):
    registration_id: str
    poll_secret: str  # Solo se muestra en esta respuesta. El bridge lo necesita para recoger el token.
    status: str = "pending"
    expires_at: datetime.datetime


class PendingRegistrationRead(BaseModel):
    registration_id: str
    code: str
    name: str
    building_id: int
    zone_id: int  # zona que pidió el bridge
    sensors: list[SensorRegistration] = Field(default_factory=list)
    status: str
    created_at: datetime.datetime
    expires_at: datetime.datetime


class ApproveRegistrationRequest(BaseModel):
    # Opcional: por defecto se usa la zona que pidió el bridge. Si se envía, debe ser del mismo edificio.
    zone_id: int | None = Field(default=None, gt=0)


class ApprovedRegistrationRead(BaseModel):
    registration_id: str
    status: str
    node_id: int
    zone_id: int
    sensor_ids: list[int] = Field(default_factory=list)  # sensores creados junto con el nodo


class DeliveredNodeRead(BaseModel):
    node_id: int
    node_code: str
    token: str  # Se entrega una sola vez.
