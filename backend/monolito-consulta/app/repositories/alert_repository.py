"""Alert repository - Create, Read, Update operations, plus the guard views."""
import datetime
from collections import Counter
from collections.abc import Sequence

from sqlalchemy import case, or_, select

from app.models.alert import Alert
from app.models.floor import Floor
from app.models.node import Node
from app.models.sensor import Sensor
from app.models.sensor_metric import SensorMetric
from app.models.zone import Zone
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert, Alert, Alert]):
    model = Alert

    async def get_by_event_uuid(self, event_uuid: str) -> Alert | None:
        """Get alert by event UUID."""
        stmt = select(Alert).where(Alert.event_uuid == event_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reading(self, reading_id: int) -> Sequence[Alert]:
        """Get alerts by reading ID."""
        stmt = select(Alert).where(Alert.reading_id == reading_id).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_handled_user(self, user_id: int) -> Sequence[Alert]:
        """Get alerts handled by a user."""
        stmt = select(Alert).where(Alert.handled_by_user_id == user_id).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unhandled(self) -> Sequence[Alert]:
        """Get unhandled alerts."""
        stmt = select(Alert).where(Alert.handled_by_user_id.is_(None)).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_open_with_context(self) -> list[dict]:
        """Alerts the guard still has to see: not ended OR not handled (a short event that ended on its own
        stays until someone handles it). With floor, zone, node, sensor and the variable's normal range.

        Order: severity emergencia, then leve, then other out-of-range (older than 24-Nov, no severity), then
        technical notices; inside each, the biggest deviation, then the newest.
        """
        stmt = (
            select(Alert, Zone.building_id, Floor.level, Floor.name, Zone.name, Node.code, Sensor.code, SensorMetric.metric_code,
                   SensorMetric.unit, SensorMetric.normal_minimum, SensorMetric.normal_maximum)
            .outerjoin(Node, Node.node_id == Alert.node_id)
            .outerjoin(Zone, Zone.zone_id == Node.zone_id)
            .outerjoin(Floor, Floor.floor_id == Zone.floor_id)
            .outerjoin(Sensor, Sensor.sensor_id == Alert.sensor_id)
            .outerjoin(SensorMetric, SensorMetric.metric_id == Alert.metric_id)
            .where(or_(Alert.ended_at.is_(None), Alert.handled_by_user_id.is_(None)))
            .order_by(case((Alert.severity == "emergencia", 0), (Alert.severity == "leve", 1),
                           (Alert.alert_type == "out_of_range", 2), else_=3), Alert.deviation.desc(),
                      Alert.started_at.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        per_building = Counter(row[1] for row in rows)
        return [
            {"alert": alert, "floor": floor, "floor_name": floor_name, "zone_name": zone_name, "node_code": node_code,
             "sensor_code": sensor_code, "metric_code": metric_code, "unit": unit,
             "normal_minimum": None if low is None else float(low),
             "normal_maximum": None if high is None else float(high),
             "other_open_count": per_building[building_id] - 1}
            for alert, building_id, floor, floor_name, zone_name, node_code, sensor_code, metric_code, unit, low, high in rows
        ]

    async def mark_handled(self, alert: Alert, user_id: int) -> Alert:
        """Record who handled it and when. It does not close the event: that happens when the data is normal."""
        alert.handled_by_user_id = user_id
        alert.handled_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def touching_window(self, sensor_id: int, metric_id: int, start: datetime.datetime,
                              end: datetime.datetime) -> Sequence[Alert]:
        """Alerts of this sensor whose episode overlaps [start, end): same variable, or technical on the sensor."""
        stmt = select(Alert).where(
            Alert.sensor_id == sensor_id,
            (Alert.metric_id == metric_id) | Alert.metric_id.is_(None),
            Alert.started_at < end,
            (Alert.ended_at.is_(None)) | (Alert.ended_at >= start),
        )
        return (await self.session.execute(stmt)).scalars().all()
