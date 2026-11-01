"""Building repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.building import Building
from app.repositories.base import BaseRepository


class BuildingRepository(BaseRepository[Building, Building, Building]):
    model = Building

    async def get_zones(self, building_id: int) -> Sequence[Building]:
        """Get zones for a building."""
        stmt = select(Building).where(Building.building_id == building_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
