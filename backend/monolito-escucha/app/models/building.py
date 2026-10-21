"""Building model."""

from sqlalchemy import BigInteger, Identity, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Building(Base):
    __tablename__ = "building"
    __table_args__ = (
        PrimaryKeyConstraint("building_id", name="building_pkey"),
    )

    building_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(250))

    zones: Mapped[list["Zone"]] = relationship("Zone", back_populates="building")
