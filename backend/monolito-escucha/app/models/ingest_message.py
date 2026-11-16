"""IngestMessage model: envelope of every message received from the bridge."""
import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IngestMessage(Base):
    __tablename__ = "ingest_message"
    __table_args__ = (
        CheckConstraint("window_start IS NULL OR window_end IS NULL OR window_end >= window_start",
                        name="chk_ingest_message_window"),
        PrimaryKeyConstraint("message_id", name="ingest_message_pkey"),
        UniqueConstraint("message_uid", name="uq_ingest_message_uid"),
        Index("idx_ingest_message_generated_at", "generated_at"),
    )

    message_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    message_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    building_code: Mapped[str | None] = mapped_column(String(50))
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(BigInteger)
    priority: Mapped[str | None] = mapped_column(String(20))
    quality: Mapped[str | None] = mapped_column(String(20))
    transport: Mapped[str | None] = mapped_column(String(20))
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False,
                                                           server_default=text("CURRENT_TIMESTAMP"))
    window_start: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    window_end: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))
    sample_count_bridge: Mapped[int | None] = mapped_column(Integer)

    readings: Mapped[list["Reading"]] = relationship("Reading", back_populates="message")
