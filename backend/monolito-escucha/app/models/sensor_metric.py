"""SensorMetric model: one variable of a sensor type with its normal and physical range."""
import decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SensorMetric(Base):
    __tablename__ = "sensor_metric"
    __table_args__ = (
        CheckConstraint(
            "normal_minimum IS NULL OR normal_maximum IS NULL OR normal_minimum <= normal_maximum",
            name="chk_sensor_metric_normal_range",
        ),
        CheckConstraint(
            "physical_minimum IS NULL OR physical_maximum IS NULL OR physical_minimum <= physical_maximum",
            name="chk_sensor_metric_physical_range",
        ),
        ForeignKeyConstraint(["sensor_type_id"], ["sensor_type.sensor_type_id"], ondelete="RESTRICT",
                             onupdate="CASCADE", name="fk_sensor_metric_sensor_type"),
        PrimaryKeyConstraint("metric_id", name="sensor_metric_pkey"),
        UniqueConstraint("sensor_type_id", "metric_code", name="uq_sensor_metric_type_code"),
    )

    metric_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    sensor_type_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(150))
    unit: Mapped[str | None] = mapped_column(String(40))
    normal_minimum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(14, 4))
    normal_maximum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(14, 4))
    physical_minimum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(14, 4))
    physical_maximum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(14, 4))
    # False = going out of range on that side is not an alarm (IAQ below 51 means cleaner air).
    alarm_below: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true(), default=True)
    alarm_above: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true(), default=True)

    sensor_type: Mapped["SensorType"] = relationship("SensorType", back_populates="metrics")
