"""ConnectivityLog model."""
import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ConnectivityLog(Base):
    __tablename__ = "connectivity_log"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="chk_connectivity_log_dates"),
        ForeignKeyConstraint(["node_id"], ["node.node_id"], ondelete="RESTRICT", onupdate="CASCADE", name="fk_connectivity_log_node"),
        PrimaryKeyConstraint("connectivity_id", name="connectivity_log_pkey"),
        Index("idx_connectivity_log_node_started_at", "node_id", "started_at"),
    )

    connectivity_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1),
        primary_key=True,
        autoincrement=True,
    )
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    node: Mapped["Node"] = relationship("Node", back_populates="connectivity_logs")
