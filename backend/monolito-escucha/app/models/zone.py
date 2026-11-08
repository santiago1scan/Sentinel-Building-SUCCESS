"""Zone model."""

from sqlalchemy import (
    BigInteger,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Zone(Base):
    __tablename__ = "zone"
    __table_args__ = (
        ForeignKeyConstraint(["building_id"], ["building.building_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_zone_building"),
        PrimaryKeyConstraint("zone_id", name="zone_pkey"),
        Index("idx_zone_building", "building_id"),
    )

    zone_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    building_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)

    building: Mapped["Building"] = relationship("Building", back_populates="zones")
    nodes: Mapped[list["Node"]] = relationship("Node", back_populates="zone")
