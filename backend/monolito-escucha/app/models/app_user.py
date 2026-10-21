"""AppUser model."""
import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        ForeignKeyConstraint(["role_code"], ["app_role.role_code"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_app_user_role"),
        PrimaryKeyConstraint("user_id", name="app_user_pkey"),
        UniqueConstraint("email", name="app_user_email_key"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    role_code: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    role: Mapped["AppRole"] = relationship("AppRole", back_populates="users")
    handled_alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="handled_by_user")
