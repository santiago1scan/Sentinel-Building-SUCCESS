"""ConnectivityLog schemas."""
import datetime

from pydantic import BaseModel, ConfigDict


class ConnectivityLogBase(BaseModel):
    node_id: int
    started_at: datetime.datetime
    ended_at: datetime.datetime | None = None


class ConnectivityLogCreate(ConnectivityLogBase):
    pass


class ConnectivityLogUpdate(BaseModel):
    node_id: int | None = None
    started_at: datetime.datetime | None = None
    ended_at: datetime.datetime | None = None


class ConnectivityLogRead(ConnectivityLogBase):
    model_config = ConfigDict(from_attributes=True)

    connectivity_id: int
