"""Sensor schemas."""

from pydantic import BaseModel, ConfigDict


class SensorBase(BaseModel):
    code: str
    primary_node_id: int
    sensor_type_id: int
    connection_type: str | None = None
    connection_address: str | None = None


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    code: str | None = None
    primary_node_id: int | None = None
    sensor_type_id: int | None = None
    connection_type: str | None = None
    connection_address: str | None = None


class SensorRead(SensorBase):
    model_config = ConfigDict(from_attributes=True)

    sensor_id: int
