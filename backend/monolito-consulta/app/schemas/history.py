"""Schemas: one row per half hour."""
import datetime

from pydantic import BaseModel


class HistoryRow(BaseModel):
    window_start: datetime.datetime
    window_end: datetime.datetime
    avg: float | None = None
    max: float | None = None
    min: float | None = None
    no_data: bool  # no summary arrived for this half hour
    alert_ids: list[int] = []  # alerts whose episode touched this half hour
