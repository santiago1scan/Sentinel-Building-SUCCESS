"""Node model."""
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
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Node(Base):
    __tablename__ = "node"
    __table_args__ = (
        CheckConstraint("local_storage_mb IS NULL OR local_storage_mb >= 0::numeric", name="chk_node_local_storage"),
        ForeignKeyConstraint(["zone_id"], ["zone.zone_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_node_zone"),
        PrimaryKeyConstraint("node_id", name="node_pkey"),
        UniqueConstraint("code", name="node_code_key"),
        Index("idx_node_zone", "zone_id"),
    )

    node_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    zone_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    registered_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    ip_address: Mapped[str | None] = mapped_column(INET)
    local_storage_mb: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 2))
    last_signal_received_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    zone: Mapped["Zone"] = relationship("Zone", back_populates="nodes")
    sensors: Mapped[list["Sensor"]] = relationship("Sensor", back_populates="primary_node")
    readings_received: Mapped[list["Reading"]] = relationship("Reading", back_populates="receiving_node")
    connectivity_logs: Mapped[list["ConnectivityLog"]] = relationship("ConnectivityLog", back_populates="node")
