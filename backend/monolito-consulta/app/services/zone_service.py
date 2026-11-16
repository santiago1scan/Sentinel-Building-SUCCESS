"""Zone service."""
from collections.abc import Sequence

from app.core.exceptions import NotFoundError, ServiceUnavailableError, UnprocessableEntityError
from app.repositories.floor_repository import FloorRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.zone import ZoneCreate, ZoneRead, ZoneUpdate


class ZoneService:
    def __init__(self, repository: ZoneRepository, floors: FloorRepository | None = None):
        self.repository = repository
        self.floors = floors

    async def _check_floor(self, building_id: int, floor_id: int | None) -> None:
        """A zone can only use a floor of its own building (the database enforces it too)."""
        if floor_id is None or self.floors is None:
            return
        floor = await self.floors.get(floor_id)
        if floor is None:
            raise NotFoundError(f"Floor with id {floor_id} not found")
        if floor.building_id != building_id:
            raise UnprocessableEntityError("The floor belongs to another building")

    async def create(self, zone_in: ZoneCreate) -> ZoneRead:
        await self._check_floor(zone_in.building_id, zone_in.floor_id)
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
        # What the zone will look like after the change: check building and floor together.
        building_id = zone_in.building_id if zone_in.building_id is not None else zone.building_id
        floor_id = zone_in.floor_id if "floor_id" in zone_in.model_fields_set else zone.floor_id
        await self._check_floor(building_id, floor_id)
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
