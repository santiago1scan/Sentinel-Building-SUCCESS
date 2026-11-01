"""AppUser schemas - password_hash excluded from response."""
import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AppUserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True
    role_code: int


class AppUserCreate(AppUserBase):
    password_hash: str


class AppUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password_hash: str | None = None
    is_active: bool | None = None
    role_code: int | None = None
    last_login_at: datetime.datetime | None = None


class AppUserRead(AppUserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    created_at: datetime.datetime
    last_login_at: datetime.datetime | None = None
