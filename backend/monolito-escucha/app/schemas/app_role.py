"""AppRole schemas."""

from pydantic import BaseModel, ConfigDict


class AppRoleBase(BaseModel):
    name: str


class AppRoleCreate(AppRoleBase):
    role_code: int


class AppRoleUpdate(BaseModel):
    name: str | None = None


class AppRoleRead(AppRoleBase):
    model_config = ConfigDict(from_attributes=True)

    role_code: int
