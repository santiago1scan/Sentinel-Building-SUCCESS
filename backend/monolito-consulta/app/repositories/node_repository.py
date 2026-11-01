"""Node repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.node import Node
from app.repositories.base import BaseRepository


class NodeRepository(BaseRepository[Node, Node, Node]):
    model = Node

    async def get_by_code(self, code: str) -> Node | None:
        """Get node by code."""
        stmt = select(Node).where(Node.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_zone(self, zone_id: int) -> Sequence[Node]:
        """Get nodes by zone ID."""
        stmt = select(Node).where(Node.zone_id == zone_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_sensors(self, node_id: int) -> Sequence[Node]:
        """Get sensors for a node."""
        stmt = select(Node).where(Node.node_id == node_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_connectivity_logs(self, node_id: int) -> Sequence[Node]:
        """Get connectivity logs for a node."""
        stmt = select(Node).where(Node.node_id == node_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_received_readings(self, node_id: int) -> Sequence[Node]:
        """Get received readings for a node."""
        stmt = select(Node).where(Node.node_id == node_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
