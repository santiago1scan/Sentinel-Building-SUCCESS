"""Floor service: floors of a building (building -> floor -> zone -> node)."""
from collections.abc import Sequence

from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.repositories.building_repository import BuildingRepository
from app.repositories.floor_repository import FloorRepository
from app.schemas.floor import FloorCreate, FloorRead, FloorUpdate


def default_floor_name(level: int) -> str:
    """Same names the migration gave to existing floors."""
    if level == 0:
        return "Planta baja"
    if level < 0:
        return f"Sótano {-level}"
    return f"Piso {level}"


class FloorService:
    def __init__(self, repository: FloorRepository, buildings: BuildingRepository):
        self.repository = repository
        self.buildings = buildings

    async def _require_building(self, building_id: int) -> None:
        if await self.buildings.get(building_id) is None:
            raise NotFoundError(f"Building with id {building_id} not found")

    async def _require_level_free(self, building_id: int, level: int, *, ignore_floor_id: int | None = None) -> None:
        other = await self.repository.get_by_building_and_level(building_id, level)
        if other is not None and other.floor_id != ignore_floor_id:
            raise ConflictError(f"Building {building_id} already has a floor with level {level}")

    async def create(self, floor_in: FloorCreate) -> FloorRead:
        await self._require_building(floor_in.building_id)
        await self._require_level_free(floor_in.building_id, floor_in.level)
        data = {
            "building_id": floor_in.building_id,
            "level": floor_in.level,
            "name": floor_in.name or default_floor_name(floor_in.level),
        }
        try:
            floor = await self.repository.create(data)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to create floor: {e}") from e
        return FloorRead.model_validate(floor)

    async def get(self, floor_id: int) -> FloorRead:
        floor = await self.repository.get(floor_id)
        if not floor:
            raise NotFoundError(f"Floor with id {floor_id} not found")
        return FloorRead.model_validate(floor)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[FloorRead]:
        try:
            floors = await self.repository.get_all(limit=limit, offset=offset)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve floors: {e}") from e
        return [FloorRead.model_validate(f) for f in floors]

    async def get_by_building(self, building_id: int) -> Sequence[FloorRead]:
        await self._require_building(building_id)
        try:
            floors = await self.repository.get_by_building(building_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve floors: {e}") from e
        return [FloorRead.model_validate(f) for f in floors]

    async def update(self, floor_id: int, floor_in: FloorUpdate) -> FloorRead:
        floor = await self.repository.get(floor_id)
        if not floor:
            raise NotFoundError(f"Floor with id {floor_id} not found")
        if floor_in.level is not None and floor_in.level != floor.level:
            await self._require_level_free(floor.building_id, floor_in.level, ignore_floor_id=floor_id)
        try:
            updated = await self.repository.update(floor, floor_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to update floor: {e}") from e
        return FloorRead.model_validate(updated)

    async def delete(self, floor_id: int) -> None:
        floor = await self.repository.get(floor_id)
        if not floor:
            raise NotFoundError(f"Floor with id {floor_id} not found")
        if await self.repository.count_zones(floor_id):
            raise ConflictError("The floor still has zones: move or delete them first")
        try:
            await self.repository.delete(floor_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to delete floor: {e}") from e
