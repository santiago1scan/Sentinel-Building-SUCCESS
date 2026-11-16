"""Floor schemas."""
from pydantic import BaseModel, ConfigDict, Field


class FloorCreate(BaseModel):
    """`level` is the number: -1 basement, 0 ground floor, 1 first floor... `name` is optional.

    Without a name it becomes "Planta baja", "Sótano N" or "Piso N".
    """

    building_id: int
    level: int
    name: str | None = Field(default=None, min_length=1, max_length=100)


class FloorUpdate(BaseModel):
    """A floor cannot move to another building: its zones belong to the old one."""

    level: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)


class FloorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    floor_id: int
    building_id: int
    level: int
    name: str
