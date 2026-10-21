"""Node schemas."""
import datetime
import decimal

from pydantic import BaseModel, ConfigDict


class NodeBase(BaseModel):
    code: str
    name: str
    zone_id: int
    ip_address: str | None = None
    local_storage_mb: decimal.Decimal | None = None
    last_signal_received_at: datetime.datetime | None = None


class NodeCreate(NodeBase):
    pass


class NodeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    zone_id: int | None = None
    ip_address: str | None = None
    local_storage_mb: decimal.Decimal | None = None
    last_signal_received_at: datetime.datetime | None = None


class NodeRead(NodeBase):
    model_config = ConfigDict(from_attributes=True)

    node_id: int
    registered_at: datetime.datetime
