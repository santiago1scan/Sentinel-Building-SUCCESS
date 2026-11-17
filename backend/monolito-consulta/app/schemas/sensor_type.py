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


class SensorMetricRead(BaseModel):
    """One variable a sensor type measures, with its normal range (None = no range: stored, never an alert)."""

    model_config = ConfigDict(from_attributes=True)

    metric_id: int
    metric_code: str
    name: str | None = None
    unit: str | None = None
    normal_minimum: decimal.Decimal | None = None
    normal_maximum: decimal.Decimal | None = None
    physical_minimum: decimal.Decimal | None = None
    physical_maximum: decimal.Decimal | None = None
    alarm_below: bool = True
    alarm_above: bool = True


class SensorTypeWithMetrics(SensorTypeRead):
    """A sensor type and the variables it measures: what the screen needs to register a sensor."""

    metrics: list[SensorMetricRead] = []
