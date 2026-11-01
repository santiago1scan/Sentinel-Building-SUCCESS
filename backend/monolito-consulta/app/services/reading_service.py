"""Reading service - Create and Read operations only."""
from collections.abc import Sequence

from app.repositories.reading_repository import ReadingRepository
from app.schemas.reading import ReadingCreate, ReadingRead


class ReadingService:
    def __init__(self, repository: ReadingRepository):
        self.repository = repository

    async def create(self, reading_in: ReadingCreate) -> ReadingRead:
        reading = await self.repository.create(reading_in)
        return ReadingRead.model_validate(reading)

    async def get(self, reading_id: int) -> ReadingRead | None:
        reading = await self.repository.get(reading_id)
        return ReadingRead.model_validate(reading) if reading else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[ReadingRead]:
        readings = await self.repository.get_all(limit=limit, offset=offset)
        return [ReadingRead.model_validate(r) for r in readings]

    async def get_by_sensor(self, sensor_id: int, limit: int = 100, offset: int = 0) -> Sequence[ReadingRead]:
        readings = await self.repository.get_by_sensor(sensor_id)
        return [ReadingRead.model_validate(r) for r in readings]

    async def get_by_receiving_node(self, receiving_node_id: int, limit: int = 100, offset: int = 0) -> Sequence[ReadingRead]:
        readings = await self.repository.get_by_receiving_node(receiving_node_id)
        return [ReadingRead.model_validate(r) for r in readings]

    async def get_by_sequence_number(self, sequence_number: int) -> Sequence[ReadingRead]:
        readings = await self.repository.get_by_sequence_number(sequence_number)
        return [ReadingRead.model_validate(r) for r in readings]

    async def get_alerts(self, reading_id: int) -> Sequence[ReadingRead]:
        readings = await self.repository.get_alerts(reading_id)
        return [ReadingRead.model_validate(r) for r in readings]
