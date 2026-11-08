"""SensorType schemas."""
import decimal

from pydantic import BaseModel, ConfigDict


class SensorTypeBase(BaseModel):
    name: str
    sampling_interval: int
    default_unit: str | None = None
    normal_minimum: decimal.Decimal | None = None
    normal_maximum: decimal.Decimal | None = None


class SensorTypeCreate(SensorTypeBase):
    pass


class SensorTypeUpdate(BaseModel):
    name: str | None = None
    sampling_interval: int | None = None
    default_unit: str | None = None
    normal_minimum: decimal.Decimal | None = None
    normal_maximum: decimal.Decimal | None = None


class SensorTypeRead(SensorTypeBase):
    model_config = ConfigDict(from_attributes=True)

    sensor_type_id: int
