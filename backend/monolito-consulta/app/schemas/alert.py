"""Alert schemas - Create, Read, Update."""
import datetime

from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    event_uuid: str
    reading_id: int
    alert_code: str
    handled_by_user_id: int | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    alert_code: str | None = None
    handled_by_user_id: int | None = None


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    alert_id: int
    generated_at: datetime.datetime
