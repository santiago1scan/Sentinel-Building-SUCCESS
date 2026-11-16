"""Zone repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.floor import Floor
from app.models.zone import Zone
from app.repositories.base import BaseRepository


class ZoneRepository(BaseRepository[Zone, Zone, Zone]):
    model = Zone

    async def get_by_building(self, building_id: int) -> Sequence[Zone]:
        """Get zones by building ID."""
        stmt = select(Zone).where(Zone.building_id == building_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_floor(self, zone: Zone) -> Floor | None:
        """Floor of a zone (None if the zone has no floor)."""
        if zone.floor_id is None:
            return None
        return await self.session.get(Floor, zone.floor_id)
