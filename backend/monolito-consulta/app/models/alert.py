"""Alert model."""
import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        ForeignKeyConstraint(["handled_by_user_id"], ["app_user.user_id"], ondelete="SET NULL", onupdate="CASCADE", name="fk_alert_handled_by_user"),
        ForeignKeyConstraint(["reading_id"], ["reading.reading_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_alert_reading"),
        PrimaryKeyConstraint("alert_id", name="alert_pkey"),
        UniqueConstraint("event_uuid", name="alert_event_uuid_key"),
        Index("idx_alert_generated_at", "generated_at"),
        Index("idx_alert_handled_by_user", "handled_by_user_id"),
    )

    alert_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    event_uuid: Mapped[str] = mapped_column(String(100), nullable=False)
    reading_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    alert_code: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    handled_by_user_id: Mapped[int | None] = mapped_column(BigInteger)

    reading: Mapped["Reading"] = relationship("Reading", back_populates="alerts")
    handled_by_user: Mapped[Optional["AppUser"]] = relationship("AppUser", back_populates="handled_alerts")
