"""AppRole model."""

from sqlalchemy import PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AppRole(Base):
    __tablename__ = "app_role"
    __table_args__ = (
        PrimaryKeyConstraint("role_code", name="app_role_pkey"),
        UniqueConstraint("name", name="app_role_name_key"),
    )

    role_code: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    users: Mapped[list["AppUser"]] = relationship("AppUser", back_populates="role")
