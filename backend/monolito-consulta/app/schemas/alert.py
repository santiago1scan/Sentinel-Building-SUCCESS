"""Alert schemas - Create, Read, Update, plus the guard views."""
import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlertBase(BaseModel):
    event_uuid: str
    alert_code: str
    reading_id: int | None = None
    handled_by_user_id: int | None = None


class AlertCreate(AlertBase):
    """Manual alert. Alerts from sensor data are created by monolito-escucha."""

    alert_type: str = Field("technical", pattern="^(out_of_range|technical)$")
    node_id: int | None = None
    sensor_id: int | None = None
    metric_id: int | None = None
    started_at: datetime.datetime | None = None
    last_seen_at: datetime.datetime | None = None

    @model_validator(mode="after")
    def _default_times(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.started_at = self.started_at or now
        self.last_seen_at = self.last_seen_at or self.started_at
        return self


class AlertUpdate(BaseModel):
    alert_code: str | None = None
    handled_by_user_id: int | None = None


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    alert_id: int
    generated_at: datetime.datetime
    alert_type: str
    direction: str | None = None
    node_id: int | None = None
    sensor_id: int | None = None
    metric_id: int | None = None
    started_at: datetime.datetime
    last_seen_at: datetime.datetime
    ended_at: datetime.datetime | None = None
    peak_value: float | None = None
    deviation: float = 0
    reading_count: int = 0
    handled_at: datetime.datetime | None = None


class OpenAlert(AlertRead):
    """What the guard sees: the alert plus where it is and what is normal for that variable."""

    floor: int | None = None
    zone_name: str | None = None
    node_code: str | None = None
    sensor_code: str | None = None
    metric_code: str | None = None
    unit: str | None = None
    normal_minimum: float | None = None
    normal_maximum: float | None = None
    other_open_count: int = 0
