"""SensorType service."""
from collections.abc import Sequence

from app.repositories.sensor_type_repository import SensorTypeRepository
from app.schemas.sensor import SensorRead
from app.schemas.sensor_type import SensorTypeCreate, SensorTypeRead, SensorTypeUpdate, SensorTypeWithMetrics


def _with_metrics(sensor_type) -> SensorTypeWithMetrics:
    result = SensorTypeWithMetrics.model_validate(sensor_type)
    result.metrics.sort(key=lambda m: m.metric_id)  # the order they were defined in
    return result


class SensorTypeService:
    def __init__(self, repository: SensorTypeRepository):
        self.repository = repository

    async def create(self, sensor_type_in: SensorTypeCreate) -> SensorTypeRead:
        sensor_type = await self.repository.create(sensor_type_in)
        return SensorTypeRead.model_validate(sensor_type)

    async def get(self, sensor_type_id: int) -> SensorTypeWithMetrics | None:
        sensor_type = await self.repository.get_with_metrics(sensor_type_id)
        return _with_metrics(sensor_type) if sensor_type else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[SensorTypeWithMetrics]:
        sensor_types = await self.repository.get_all_with_metrics(limit=limit, offset=offset)
        return [_with_metrics(st) for st in sensor_types]

    async def update(self, sensor_type_id: int, sensor_type_in: SensorTypeUpdate) -> SensorTypeRead | None:
        sensor_type = await self.repository.get(sensor_type_id)
        if not sensor_type:
            return None
        updated = await self.repository.update(sensor_type, sensor_type_in)
        return SensorTypeRead.model_validate(updated)

    async def delete(self, sensor_type_id: int) -> bool:
        return await self.repository.delete(sensor_type_id)

    async def get_sensors(self, sensor_type_id: int) -> Sequence[SensorRead]:
        sensors = await self.repository.get_sensors(sensor_type_id)
        return [SensorRead.model_validate(s) for s in sensors]
