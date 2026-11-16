"""Half-hour history of one sensor variable (avg, max, min), with the gaps marked as no data."""
import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading import Reading
from app.models.sensor import Sensor
from app.models.sensor_metric import SensorMetric
from app.repositories.alert_repository import AlertRepository
from app.schemas.history import HistoryRow

WINDOW = datetime.timedelta(minutes=30)
MAX_WINDOWS = 31 * 48  # one month of half hours per request


class MetricNotFound(LookupError):
    pass


def _floor_to_half_hour(at: datetime.datetime) -> datetime.datetime:
    return at.replace(minute=0 if at.minute < 30 else 30, second=0, microsecond=0)


class HistoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def half_hours(self, sensor_id: int, metric_code: str, start: datetime.datetime,
                         end: datetime.datetime) -> list[HistoryRow]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("from and to need a time zone (e.g. 2026-11-13T10:00:00-05:00)")
        if end <= start:
            raise ValueError("to must be after from")
        metric = (await self.session.execute(
            select(SensorMetric).join(Sensor, Sensor.sensor_type_id == SensorMetric.sensor_type_id)
            .where(Sensor.sensor_id == sensor_id, SensorMetric.metric_code == metric_code))).scalar_one_or_none()
        if metric is None:
            raise MetricNotFound(f"Sensor {sensor_id} has no variable {metric_code}")

        first = _floor_to_half_hour(start.astimezone(datetime.timezone.utc))  # half hours counted in UTC
        count = -(-(end - first) // WINDOW)  # ceil
        if count > MAX_WINDOWS:
            raise ValueError(f"At most {MAX_WINDOWS} half hours per request")

        readings = (await self.session.execute(
            select(Reading.measured_at, Reading.aggregation, Reading.measured_value).where(
                Reading.sensor_id == sensor_id, Reading.metric_id == metric.metric_id,
                Reading.aggregation.in_(("avg", "max", "min")),
                Reading.measured_at >= first, Reading.measured_at < first + count * WINDOW,
            ))).all()
        by_window: dict[datetime.datetime, dict[str, float]] = {}
        for measured_at, aggregation, value in readings:
            key = _floor_to_half_hour(measured_at.astimezone(datetime.timezone.utc))
            by_window.setdefault(key, {})[aggregation] = float(value)

        alerts = await AlertRepository(self.session).touching_window(
            sensor_id, metric.metric_id, first, first + count * WINDOW)

        rows = []
        for i in range(count):
            w_start = first + i * WINDOW
            w_end = w_start + WINDOW
            values = by_window.get(w_start, {})
            touching = sorted(a.alert_id for a in alerts
                              if a.started_at < w_end and (a.ended_at is None or a.ended_at >= w_start))
            rows.append(HistoryRow(window_start=w_start, window_end=w_end, avg=values.get("avg"),
                                   max=values.get("max"), min=values.get("min"), no_data=not values,
                                   alert_ids=touching))
        return rows
