"""Sensor model."""

from sqlalchemy import (
    BigInteger,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Sensor(Base):
    __tablename__ = "sensor"
    __table_args__ = (
        ForeignKeyConstraint(["primary_node_id"], ["node.node_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_sensor_primary_node"),
        ForeignKeyConstraint(["sensor_type_id"], ["sensor_type.sensor_type_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_sensor_sensor_type"),
        PrimaryKeyConstraint("sensor_id", name="sensor_pkey"),
        UniqueConstraint("code", name="sensor_code_key"),
        Index("idx_sensor_primary_node", "primary_node_id"),
        Index("idx_sensor_sensor_type", "sensor_type_id"),
    )

    sensor_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sensor_type_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    connection_type: Mapped[str | None] = mapped_column(String(50))
    connection_address: Mapped[str | None] = mapped_column(String(250))

    primary_node: Mapped["Node"] = relationship("Node", back_populates="sensors")
    sensor_type: Mapped["SensorType"] = relationship("SensorType", back_populates="sensors")
    readings: Mapped[list["Reading"]] = relationship("Reading", back_populates="sensor")
