"""SensorType repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.sensor_type import SensorType
from app.repositories.base import BaseRepository


class SensorTypeRepository(BaseRepository[SensorType, SensorType, SensorType]):
    model = SensorType

    async def get_sensors(self, sensor_type_id: int) -> Sequence[SensorType]:
        """Get sensors for a sensor type."""
        stmt = select(SensorType).where(SensorType.sensor_type_id == sensor_type_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
