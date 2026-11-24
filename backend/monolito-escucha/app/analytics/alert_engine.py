"""Alert engine: groups out-of-range readings into one alert and opens technical notices.

The system does not interpret what is happening (fire, earthquake): it shows the guard what left its normal range.
Business rules confirmed on 13-Nov-2026:
- An event ends when the incoming data is normal again: an in-range reading of that sensor and variable, or a
  half-hour summary whose max AND min are in range (the average alone can hide a short peak).
- IAQ below 51 is cleaner air, not an alarm (sensor_metric.alarm_below = false).
Technical notices never count as emergencies: alert_type = "technical".
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.analytics.ranges import RangeLike, deviation, evaluate
from app.analytics.severity import EMERGENCIA, classify_node
from app.models.alert import Alert

OUT_OF_RANGE = "out_of_range"
TECHNICAL = "technical"

SENSOR_IMPOSSIBLE = "SENSOR_IMPOSSIBLE"
SENSOR_STUCK = "SENSOR_STUCK"
BATTERY_LOW = "BATTERY_LOW"
ON_BATTERY_POWER = "ON_BATTERY_POWER"  # power_source = battery
NODE_SILENT = "NODE_SILENT"

# Four flat summaries in a row = two hours with max == min.
STUCK_SUMMARIES = 4


class MetricLike(RangeLike, Protocol):
    metric_id: int
    metric_code: str


class AlertStore(Protocol):
    async def find_open(self, *, alert_type: str, alert_code: str, sensor_id: int | None = None,
                        metric_id: int | None = None, node_id: int | None = None,
                        direction: str | None = None) -> Alert | None: ...

    async def open_out_of_range(self, sensor_id: int, metric_id: int) -> list[Alert]: ...

    async def open_out_of_range_by_node(self, node_id: int) -> list[tuple[Alert, str]]:
        """Open out-of-range alerts of a node, each with the metric_code of its variable."""
        ...

    async def add(self, alert: Alert) -> Alert: ...

    async def recent_summary_extremes(self, sensor_id: int, metric_id: int, limit: int) -> list[tuple[float, float]]:
        """(max, min) of the latest half-hour summaries, newest first, including the one being processed."""
        ...


def _dec(value: float) -> Decimal:
    return Decimal(str(round(value, 4)))


class AlertEngine:
    def __init__(self, store: AlertStore):
        self.store = store

    # --- helpers -------------------------------------------------------------------------------------------
    async def _open_or_extend(self, *, alert_type: str, alert_code: str, at: datetime, node_id: int | None,
                              sensor_id: int | None = None, metric_id: int | None = None,
                              direction: str | None = None, value: float | None = None, dev: float = 0,
                              reading_id: int | None = None, count: bool = True) -> Alert:
        alert = await self.store.find_open(alert_type=alert_type, alert_code=alert_code, sensor_id=sensor_id,
                                           metric_id=metric_id, node_id=node_id, direction=direction)
        if alert is None:
            alert = Alert(
                event_uuid=str(uuid.uuid4()), alert_type=alert_type, alert_code=alert_code, direction=direction,
                node_id=node_id, sensor_id=sensor_id, metric_id=metric_id, reading_id=reading_id,
                started_at=at, last_seen_at=at, generated_at=at,
                peak_value=None if value is None else _dec(value), deviation=_dec(dev),
                reading_count=1 if count else 0,
            )
            return await self.store.add(alert)
        alert.last_seen_at = max(alert.last_seen_at, at)
        if count:
            alert.reading_count = (alert.reading_count or 0) + 1
        if value is not None and dev >= float(alert.deviation or 0):
            alert.peak_value, alert.deviation = _dec(value), _dec(dev)
        return alert

    async def _close(self, alert: Alert | None, at: datetime) -> None:
        # Data older than the alert's last reading (a bridge retry arriving late) says nothing about now.
        if alert is not None and alert.ended_at is None and at >= alert.last_seen_at:
            alert.ended_at = at

    async def _close_out_of_range(self, sensor_id: int, metric: MetricLike, at: datetime) -> None:
        for alert in await self.store.open_out_of_range(sensor_id, metric.metric_id):
            await self._close(alert, at)

    async def _close_technical(self, code: str, at: datetime, *, node_id: int | None, sensor_id: int | None = None,
                               metric_id: int | None = None) -> None:
        alert = await self.store.find_open(alert_type=TECHNICAL, alert_code=code, sensor_id=sensor_id,
                                           metric_id=metric_id, node_id=node_id)
        await self._close(alert, at)

    # --- out-of-range grouping + impossible values -------------------------------------------------------------------------
    async def on_raw(self, sensor_id: int, node_id: int, metric: MetricLike, value: float, at: datetime,
                     reading_id: int | None = None) -> Alert | None:
        """An incident value. Returns the alert the reading belongs to, or None."""
        status = evaluate(value, metric)
        if status == "impossible":
            return await self._open_or_extend(alert_type=TECHNICAL, alert_code=SENSOR_IMPOSSIBLE, at=at,
                                              node_id=node_id, sensor_id=sensor_id, metric_id=metric.metric_id,
                                              value=value, reading_id=reading_id)
        if status in ("above", "below"):
            opposite = "below" if status == "above" else "above"
            await self._close(await self.store.find_open(
                alert_type=OUT_OF_RANGE, alert_code=f"OUT_OF_RANGE_{opposite.upper()}", sensor_id=sensor_id,
                metric_id=metric.metric_id, node_id=node_id, direction=opposite), at)
            return await self._open_or_extend(
                alert_type=OUT_OF_RANGE, alert_code=f"OUT_OF_RANGE_{status.upper()}", at=at, node_id=node_id,
                sensor_id=sensor_id, metric_id=metric.metric_id, direction=status, value=value,
                dev=deviation(value, metric), reading_id=reading_id)
        if status == "normal":
            await self._close_out_of_range(sensor_id, metric, at)
            await self._close_technical(SENSOR_IMPOSSIBLE, at, node_id=node_id, sensor_id=sensor_id,
                                        metric_id=metric.metric_id)
        return None

    # --- half-hour summary --------------------------------------------------------------------------------
    async def on_summary(self, sensor_id: int, node_id: int, metric: MetricLike, *, avg: float | None,
                         max_: float | None, min_: float | None, window_end: datetime) -> None:
        extremes = [v for v in (max_, min_) if v is not None]
        statuses = [evaluate(v, metric) for v in extremes]

        if "impossible" in statuses:
            worst = max(extremes, key=lambda v: abs(v))
            await self._open_or_extend(alert_type=TECHNICAL, alert_code=SENSOR_IMPOSSIBLE, at=window_end,
                                       node_id=node_id, sensor_id=sensor_id, metric_id=metric.metric_id,
                                       value=worst)
        elif max_ is not None and min_ is not None and all(s == "normal" for s in statuses):
            await self._close_out_of_range(sensor_id, metric, window_end)
            await self._close_technical(SENSOR_IMPOSSIBLE, window_end, node_id=node_id, sensor_id=sensor_id,
                                        metric_id=metric.metric_id)

        if max_ is None or min_ is None:
            return
        if max_ != min_:
            await self._close_technical(SENSOR_STUCK, window_end, node_id=node_id, sensor_id=sensor_id,
                                        metric_id=metric.metric_id)
            return
        recent = await self.store.recent_summary_extremes(sensor_id, metric.metric_id, STUCK_SUMMARIES)
        if len(recent) >= STUCK_SUMMARIES and all(mx == mn for mx, mn in recent):
            await self._open_or_extend(alert_type=TECHNICAL, alert_code=SENSOR_STUCK, at=window_end,
                                       node_id=node_id, sensor_id=sensor_id, metric_id=metric.metric_id,
                                       value=max_)

    # --- severity (per node) -------------------------------------------------------------------------------------------
    async def apply_severity(self, node_id: int) -> None:
        """Grade the node's open out-of-range alerts (app/analytics/severity.py). Run after the node's readings.

        An emergency is never lowered back to minor: the history keeps the worst the alert was.
        """
        open_alerts = await self.store.open_out_of_range_by_node(node_id)
        severity = classify_node(code for _, code in open_alerts)
        if severity is None:
            return
        for alert, _ in open_alerts:
            if alert.severity != EMERGENCIA:
                alert.severity = severity

    # --- technical notices: battery and silence (per node) --------------------------------------------------------------
    async def on_battery(self, node_id: int, sensor_id: int, metric: MetricLike, flag: float, at: datetime,
                         code: str = BATTERY_LOW) -> None:
        """A yes/no flag of the node's power: 1 opens (or keeps) the technical notice, 0 closes it."""
        if flag >= 1:
            await self._open_or_extend(alert_type=TECHNICAL, alert_code=code, at=at, node_id=node_id,
                                       sensor_id=sensor_id, metric_id=metric.metric_id)
        else:
            await self._close_technical(code, at, node_id=node_id, sensor_id=sensor_id,
                                        metric_id=metric.metric_id)

    async def open_node_silent(self, node_id: int, at: datetime) -> Alert:
        return await self._open_or_extend(alert_type=TECHNICAL, alert_code=NODE_SILENT, at=at, node_id=node_id,
                                          count=False)

    async def on_node_heard(self, node_id: int, at: datetime) -> None:
        await self._close_technical(NODE_SILENT, at, node_id=node_id)
