"""Floor repository."""
from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.floor import Floor
from app.models.zone import Zone
from app.repositories.base import BaseRepository


class FloorRepository(BaseRepository[Floor, Floor, Floor]):
    model = Floor

    async def get_by_building(self, building_id: int) -> Sequence[Floor]:
        """Floors of a building, from the lowest level up."""
        stmt = select(Floor).where(Floor.building_id == building_id).order_by(Floor.level)
        return (await self.session.execute(stmt)).scalars().all()

    async def get_by_building_and_level(self, building_id: int, level: int) -> Floor | None:
        stmt = select(Floor).where(Floor.building_id == building_id, Floor.level == level)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_zones(self, floor_id: int) -> int:
        stmt = select(func.count(Zone.zone_id)).where(Zone.floor_id == floor_id)
        return (await self.session.execute(stmt)).scalar_one()
