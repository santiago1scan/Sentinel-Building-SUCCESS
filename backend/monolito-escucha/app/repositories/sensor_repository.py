"""Sensor repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.sensor import Sensor
from app.repositories.base import BaseRepository


class SensorRepository(BaseRepository[Sensor, Sensor, Sensor]):
    model = Sensor

    async def get_by_code(self, code: str) -> Sensor | None:
        """Get sensor by code."""
        stmt = select(Sensor).where(Sensor.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_primary_node(self, primary_node_id: int) -> Sequence[Sensor]:
        """Get sensors by primary node ID."""
        stmt = select(Sensor).where(Sensor.primary_node_id == primary_node_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_sensor_type(self, sensor_type_id: int) -> Sequence[Sensor]:
        """Get sensors by sensor type ID."""
        stmt = select(Sensor).where(Sensor.sensor_type_id == sensor_type_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_readings(self, sensor_id: int) -> Sequence[Sensor]:
        """Get readings for a sensor."""
        stmt = select(Sensor).where(Sensor.sensor_id == sensor_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
