"""Zone schemas."""

from pydantic import BaseModel, ConfigDict


class ZoneBase(BaseModel):
    building_id: int
    name: str
    floor: int | None = None


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdate(BaseModel):
    building_id: int | None = None
    name: str | None = None
    floor: int | None = None


class ZoneRead(ZoneBase):
    model_config = ConfigDict(from_attributes=True)

    zone_id: int
