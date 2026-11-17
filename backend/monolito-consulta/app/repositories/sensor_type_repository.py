"""SensorType repository."""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.sensor import Sensor
from app.models.sensor_type import SensorType
from app.repositories.base import BaseRepository


class SensorTypeRepository(BaseRepository[SensorType, SensorType, SensorType]):
    model = SensorType

    async def get_with_metrics(self, sensor_type_id: int) -> SensorType | None:
        stmt = (select(SensorType).options(selectinload(SensorType.metrics))
                .where(SensorType.sensor_type_id == sensor_type_id))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_all_with_metrics(self, limit: int = 100, offset: int = 0) -> Sequence[SensorType]:
        stmt = (select(SensorType).options(selectinload(SensorType.metrics))
                .order_by(SensorType.sensor_type_id).limit(limit).offset(offset))
        return (await self.session.execute(stmt)).scalars().all()

    async def get_sensors(self, sensor_type_id: int) -> Sequence[Sensor]:
        """Sensors of a sensor type (it returned the type itself before)."""
        stmt = select(Sensor).where(Sensor.sensor_type_id == sensor_type_id).order_by(Sensor.sensor_id)
        return (await self.session.execute(stmt)).scalars().all()
