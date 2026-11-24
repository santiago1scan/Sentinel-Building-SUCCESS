"""Alert model."""
import datetime
import decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
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
        ForeignKeyConstraint(["node_id"], ["node.node_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_alert_node"),
        ForeignKeyConstraint(["sensor_id"], ["sensor.sensor_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_alert_sensor"),
        ForeignKeyConstraint(["metric_id"], ["sensor_metric.metric_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_alert_metric"),
        CheckConstraint("alert_type IN ('out_of_range', 'technical')", name="chk_alert_type"),
        CheckConstraint("direction IS NULL OR direction IN ('above', 'below')", name="chk_alert_direction"),
        Index("idx_alert_open", "ended_at", "alert_type"),
    )

    alert_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    event_uuid: Mapped[str] = mapped_column(String(100), nullable=False)
    # First reading of the episode; technical alerts (node silent, battery) have none.
    reading_id: Mapped[int | None] = mapped_column(BigInteger)
    alert_code: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    handled_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)  # out_of_range | technical
    direction: Mapped[str | None] = mapped_column(String(10))  # above | below (out_of_range only)
    node_id: Mapped[int | None] = mapped_column(BigInteger)
    sensor_id: Mapped[int | None] = mapped_column(BigInteger)
    metric_id: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    last_seen_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))  # None = still open
    peak_value: Mapped[decimal.Decimal | None] = mapped_column(Numeric(14, 4))
    deviation: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False, server_default="0", default=0)
    reading_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    handled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    # emergencia | leve, set by monolito-escucha (app/analytics/severity.py). NULL: technical or older than 24-Nov.
    severity: Mapped[str | None] = mapped_column(String(20))

    reading: Mapped[Optional["Reading"]] = relationship("Reading", back_populates="alerts", foreign_keys=[reading_id])
    handled_by_user: Mapped[Optional["AppUser"]] = relationship("AppUser", back_populates="handled_alerts")
