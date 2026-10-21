"""SensorType model."""
import decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Identity,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SensorType(Base):
    __tablename__ = "sensor_type"
    __table_args__ = (
        CheckConstraint(
            "normal_minimum IS NULL OR normal_maximum IS NULL OR normal_minimum <= normal_maximum",
            name="chk_sensor_type_normal_range",
        ),
        CheckConstraint("sampling_interval > 0", name="chk_sensor_type_sampling_interval"),
        PrimaryKeyConstraint("sensor_type_id", name="sensor_type_pkey"),
        UniqueConstraint("name", name="sensor_type_name_key"),
    )

    sensor_type_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sampling_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    default_unit: Mapped[str | None] = mapped_column(String(40))
    normal_minimum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 4))
    normal_maximum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 4))

    sensors: Mapped[list["Sensor"]] = relationship("Sensor", back_populates="sensor_type")
