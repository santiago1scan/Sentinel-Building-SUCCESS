"""Sensor service."""
from collections.abc import Sequence

from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate


class SensorService:
    def __init__(self, repository: SensorRepository):
        self.repository = repository

    async def create(self, sensor_in: SensorCreate) -> SensorRead:
        sensor = await self.repository.create(sensor_in)
        return SensorRead.model_validate(sensor)

    async def get(self, sensor_id: int) -> SensorRead | None:
        sensor = await self.repository.get(sensor_id)
        return SensorRead.model_validate(sensor) if sensor else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[SensorRead]:
        sensors = await self.repository.get_all(limit=limit, offset=offset)
        return [SensorRead.model_validate(s) for s in sensors]

    async def update(self, sensor_id: int, sensor_in: SensorUpdate) -> SensorRead | None:
        sensor = await self.repository.get(sensor_id)
        if not sensor:
            return None
        updated = await self.repository.update(sensor, sensor_in)
        return SensorRead.model_validate(updated)

    async def delete(self, sensor_id: int) -> bool:
        return await self.repository.delete(sensor_id)

    async def get_by_code(self, code: str) -> SensorRead | None:
        sensor = await self.repository.get_by_code(code)
        return SensorRead.model_validate(sensor) if sensor else None

    async def get_by_primary_node(self, primary_node_id: int) -> Sequence[SensorRead]:
        sensors = await self.repository.get_by_primary_node(primary_node_id)
        return [SensorRead.model_validate(s) for s in sensors]

    async def get_by_sensor_type(self, sensor_type_id: int) -> Sequence[SensorRead]:
        sensors = await self.repository.get_by_sensor_type(sensor_type_id)
        return [SensorRead.model_validate(s) for s in sensors]

    async def get_readings(self, sensor_id: int) -> Sequence[SensorRead]:
        sensors = await self.repository.get_readings(sensor_id)
        return [SensorRead.model_validate(s) for s in sensors]
