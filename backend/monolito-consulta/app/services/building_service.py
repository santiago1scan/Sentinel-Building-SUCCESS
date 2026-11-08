"""Building service."""
from collections.abc import Sequence

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.repositories.building_repository import BuildingRepository
from app.schemas.building import BuildingCreate, BuildingRead, BuildingUpdate


class BuildingService:
    def __init__(self, repository: BuildingRepository):
        self.repository = repository

    async def create(self, building_in: BuildingCreate) -> BuildingRead:
        try:
            building = await self.repository.create(building_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to create building: {e}") from e
        return BuildingRead.model_validate(building)

    async def get(self, building_id: int) -> BuildingRead:
        building = await self.repository.get(building_id)
        if not building:
            raise NotFoundError(f"Building with id {building_id} not found")
        return BuildingRead.model_validate(building)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[BuildingRead]:
        try:
            buildings = await self.repository.get_all(limit=limit, offset=offset)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve buildings: {e}") from e
        return [BuildingRead.model_validate(b) for b in buildings]

    async def update(self, building_id: int, building_in: BuildingUpdate) -> BuildingRead:
        building = await self.repository.get(building_id)
        if not building:
            raise NotFoundError(f"Building with id {building_id} not found")
        try:
            updated = await self.repository.update(building, building_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to update building: {e}") from e
        return BuildingRead.model_validate(updated)

    async def delete(self, building_id: int) -> None:
        building = await self.repository.get(building_id)
        if not building:
            raise NotFoundError(f"Building with id {building_id} not found")
        try:
            await self.repository.delete(building_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to delete building: {e}") from e

    async def get_zones(self, building_id: int) -> Sequence[BuildingRead]:
        building = await self.repository.get(building_id)
        if not building:
            raise NotFoundError(f"Building with id {building_id} not found")
        try:
            buildings = await self.repository.get_zones(building_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve zones: {e}") from e
        return [BuildingRead.model_validate(b) for b in buildings]
