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
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
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
        CheckConstraint("aggregation IN ('raw', 'avg', 'max', 'min')", name="chk_reading_aggregation"),
        ForeignKeyConstraint(["message_id"], ["ingest_message.message_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_reading_message"),
        ForeignKeyConstraint(["metric_id"], ["sensor_metric.metric_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_reading_metric"),
        ForeignKeyConstraint(["alert_id"], ["alert.alert_id"], ondelete="SET NULL", onupdate="CASCADE", name="fk_reading_alert", use_alter=True),
        UniqueConstraint("message_id", "sensor_id", "metric_id", "aggregation", name="uq_reading_message_sensor_metric_aggregation"),
        Index("idx_reading_sensor_metric_measured_at", "sensor_id", "metric_id", "measured_at"),
        Index("idx_reading_alert", "alert_id"),
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
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metric_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # raw = an incident value sent right away; avg/max/min = the half-hour summary.
    aggregation: Mapped[str] = mapped_column(String(10), nullable=False)
    sample_count_sensor: Mapped[int | None] = mapped_column(Integer)
    alert_id: Mapped[int | None] = mapped_column(BigInteger)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="readings")
    receiving_node: Mapped["Node"] = relationship("Node", back_populates="readings_received")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="reading", foreign_keys="Alert.reading_id")
    message: Mapped["IngestMessage"] = relationship("IngestMessage", back_populates="readings")
    metric: Mapped["SensorMetric"] = relationship("SensorMetric")
