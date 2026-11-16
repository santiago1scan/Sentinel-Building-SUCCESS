"""Floor model: one floor (level) of a building.

Hierarchy: building -> floor -> zone -> node. A node knows its floor through its zone.
`level` is the number (-1 basement, 0 ground floor, 1 first floor...); `name` is what people read.
"""
from sqlalchemy import (
    BigInteger,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Floor(Base):
    __tablename__ = "floor"
    __table_args__ = (
        ForeignKeyConstraint(["building_id"], ["building.building_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_floor_building"),
        PrimaryKeyConstraint("floor_id", name="floor_pkey"),
        # A building cannot have two floors with the same number.
        UniqueConstraint("building_id", "level", name="uq_floor_building_level"),
        # Target of zone's composite foreign key: a zone can only use a floor of its own building.
        UniqueConstraint("floor_id", "building_id", name="uq_floor_id_building"),
        Index("idx_floor_building", "building_id"),
    )

    floor_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    building_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    building: Mapped["Building"] = relationship("Building", back_populates="floors")
    zones: Mapped[list["Zone"]] = relationship(
        "Zone", back_populates="floor", primaryjoin="Zone.floor_id == Floor.floor_id", foreign_keys="[Zone.floor_id]"
    )
