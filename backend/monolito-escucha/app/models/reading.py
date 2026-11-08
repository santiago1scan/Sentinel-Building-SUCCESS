"""Reading model."""
import datetime
import decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Reading(Base):
    __tablename__ = "reading"
    __table_args__ = (
        CheckConstraint("sequence_number IS NULL OR sequence_number >= 0", name="chk_reading_sequence_number"),
        ForeignKeyConstraint(["receiving_node_id"], ["node.node_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_reading_receiving_node"),
        ForeignKeyConstraint(["sensor_id"], ["sensor.sensor_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_reading_sensor"),
        PrimaryKeyConstraint("reading_id", name="reading_pkey"),
        Index("idx_reading_receiving_node_received_at", "receiving_node_id", "received_at"),
        Index("idx_reading_sensor_measured_at", "sensor_id", "measured_at"),
    )

    reading_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    sensor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receiving_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    measured_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    measured_value: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(BigInteger)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="readings")
    receiving_node: Mapped["Node"] = relationship("Node", back_populates="readings_received")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="reading")
