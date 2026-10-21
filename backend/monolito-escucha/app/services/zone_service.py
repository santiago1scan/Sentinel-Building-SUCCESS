"""Zone service."""
from collections.abc import Sequence

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.repositories.zone_repository import ZoneRepository
from app.schemas.zone import ZoneCreate, ZoneRead, ZoneUpdate


class ZoneService:
    def __init__(self, repository: ZoneRepository):
        self.repository = repository

    async def create(self, zone_in: ZoneCreate) -> ZoneRead:
        try:
            zone = await self.repository.create(zone_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to create zone: {e}") from e
        return ZoneRead.model_validate(zone)

    async def get(self, zone_id: int) -> ZoneRead:
        zone = await self.repository.get(zone_id)
        if not zone:
            raise NotFoundError(f"Zone with id {zone_id} not found")
        return ZoneRead.model_validate(zone)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[ZoneRead]:
        try:
            zones = await self.repository.get_all(limit=limit, offset=offset)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve zones: {e}") from e
        return [ZoneRead.model_validate(z) for z in zones]

    async def update(self, zone_id: int, zone_in: ZoneUpdate) -> ZoneRead:
        zone = await self.repository.get(zone_id)
        if not zone:
            raise NotFoundError(f"Zone with id {zone_id} not found")
        try:
            updated = await self.repository.update(zone, zone_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to update zone: {e}") from e
        return ZoneRead.model_validate(updated)

    async def delete(self, zone_id: int) -> None:
        zone = await self.repository.get(zone_id)
        if not zone:
            raise NotFoundError(f"Zone with id {zone_id} not found")
        try:
            await self.repository.delete(zone_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to delete zone: {e}") from e

    async def get_by_building(self, building_id: int) -> Sequence[ZoneRead]:
        try:
            zones = await self.repository.get_by_building(building_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve zones: {e}") from e
        return [ZoneRead.model_validate(z) for z in zones]
