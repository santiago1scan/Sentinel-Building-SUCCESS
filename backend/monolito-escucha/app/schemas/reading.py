"""Reading schemas - Create and Read only."""
import datetime
import decimal

from pydantic import BaseModel, ConfigDict


class ReadingBase(BaseModel):
    sensor_id: int
    receiving_node_id: int
    measured_at: datetime.datetime
    measured_value: decimal.Decimal
    sequence_number: int | None = None


class ReadingCreate(ReadingBase):
    pass


class ReadingRead(ReadingBase):
    model_config = ConfigDict(from_attributes=True)

    reading_id: int
    received_at: datetime.datetime
