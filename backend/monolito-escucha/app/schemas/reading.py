"""Reading schemas - Create and Read only."""
import datetime
import decimal

from pydantic import BaseModel, ConfigDict, Field


class ReadingBase(BaseModel):
    sensor_id: int
    receiving_node_id: int
    measured_at: datetime.datetime
    measured_value: decimal.Decimal
    sequence_number: int | None = None


class ReadingCreate(ReadingBase):
    message_id: int
    metric_id: int
    aggregation: str = Field(pattern="^(raw|avg|max|min)$")
    sample_count_sensor: int | None = None


class ReadingRead(ReadingBase):
    model_config = ConfigDict(from_attributes=True)

    reading_id: int
    received_at: datetime.datetime
    message_id: int | None = None
    metric_id: int | None = None
    aggregation: str | None = None  # raw = incident; avg/max/min = half-hour summary
    sample_count_sensor: int | None = None
    alert_id: int | None = None
