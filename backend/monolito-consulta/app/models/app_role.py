"""AppRole model."""

from sqlalchemy import BigInteger, Identity, PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AppRole(Base):
    __tablename__ = "app_role"
    __table_args__ = (
        PrimaryKeyConstraint("role_code", name="app_role_pkey"),
        UniqueConstraint("name", name="app_role_name_key"),
    )

    role_code: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    users: Mapped[list["AppUser"]] = relationship("AppUser", back_populates="role")
