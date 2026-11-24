"""Repositories for the analytics tables: ingest_message, sensor_metric and alert (the AlertStore of the engine)."""
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.analytics.ranges import DEFAULT_RANGES
from app.models.alert import Alert
from app.models.ingest_message import IngestMessage
from app.models.reading import Reading
from app.models.sensor_metric import SensorMetric


def _dec(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class IngestMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_uid(self, message_uid: str) -> IngestMessage | None:
        result = await self.session.execute(select(IngestMessage).where(IngestMessage.message_uid == message_uid))
        return result.scalar_one_or_none()

    async def add(self, message: IngestMessage) -> IngestMessage:
        self.session.add(message)
        await self.session.flush()
        return message


class SensorMetricRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[tuple[int, str], SensorMetric] = {}

    async def get_or_create(self, sensor_type_id: int, metric_code: str) -> SensorMetric:
        """A variable seen for the first time is created with the Excel defaults, or without range."""
        key = (sensor_type_id, metric_code)
        if key in self._cache:
            return self._cache[key]
        result = await self.session.execute(select(SensorMetric).where(
            SensorMetric.sensor_type_id == sensor_type_id, SensorMetric.metric_code == metric_code))
        metric = result.scalar_one_or_none()
        if metric is None:
            r = DEFAULT_RANGES.get(metric_code)
            metric = SensorMetric(sensor_type_id=sensor_type_id, metric_code=metric_code)
            if r is not None:
                metric.unit = r.unit
                metric.normal_minimum, metric.normal_maximum = _dec(r.normal_minimum), _dec(r.normal_maximum)
                metric.physical_minimum, metric.physical_maximum = _dec(r.physical_minimum), _dec(r.physical_maximum)
                metric.alarm_below, metric.alarm_above = r.alarm_below, r.alarm_above
            self.session.add(metric)
            await self.session.flush()
        self._cache[key] = metric
        return metric


class AlertRepository:
    """Implements app.analytics.alert_engine.AlertStore."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_open(self, *, alert_type, alert_code, sensor_id=None, metric_id=None, node_id=None,
                        direction=None) -> Alert | None:
        def eq(column, value):
            return column.is_(None) if value is None else column == value

        stmt = select(Alert).where(
            Alert.ended_at.is_(None), Alert.alert_type == alert_type, Alert.alert_code == alert_code,
            eq(Alert.sensor_id, sensor_id), eq(Alert.metric_id, metric_id), eq(Alert.node_id, node_id),
            eq(Alert.direction, direction),
        ).order_by(Alert.started_at.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def open_out_of_range(self, sensor_id: int, metric_id: int) -> list[Alert]:
        stmt = select(Alert).where(Alert.ended_at.is_(None), Alert.alert_type == "out_of_range",
                                   Alert.sensor_id == sensor_id, Alert.metric_id == metric_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def open_out_of_range_by_node(self, node_id: int) -> list[tuple[Alert, str]]:
        stmt = (select(Alert, SensorMetric.metric_code)
                .join(SensorMetric, SensorMetric.metric_id == Alert.metric_id)
                .where(Alert.ended_at.is_(None), Alert.alert_type == "out_of_range", Alert.node_id == node_id))
        return [(alert, code) for alert, code in (await self.session.execute(stmt)).all()]

    async def add(self, alert: Alert) -> Alert:
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def recent_summary_extremes(self, sensor_id: int, metric_id: int, limit: int) -> list[tuple[float, float]]:
        r_max, r_min = aliased(Reading), aliased(Reading)
        stmt = (
            select(r_max.measured_value, r_min.measured_value)
            .join(r_min, and_(r_min.message_id == r_max.message_id, r_min.sensor_id == r_max.sensor_id,
                              r_min.metric_id == r_max.metric_id, r_min.aggregation == "min"))
            .where(r_max.sensor_id == sensor_id, r_max.metric_id == metric_id, r_max.aggregation == "max")
            .order_by(r_max.measured_at.desc())
            .limit(limit)
        )
        return [(float(mx), float(mn)) for mx, mn in (await self.session.execute(stmt)).all()]
