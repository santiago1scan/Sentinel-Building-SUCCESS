"""Building schemas."""
from pydantic import BaseModel, ConfigDict


class BuildingBase(BaseModel):
    name: str
    address: str | None = None


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: str | None = None
    address: str | None = None


class BuildingRead(BuildingBase):
    model_config = ConfigDict(from_attributes=True)

    building_id: int
