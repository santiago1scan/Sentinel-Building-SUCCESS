"""ConnectivityLog repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.connectivity_log import ConnectivityLog
from app.repositories.base import BaseRepository


class ConnectivityLogRepository(BaseRepository[ConnectivityLog, ConnectivityLog, ConnectivityLog]):
    model = ConnectivityLog

    async def get_by_node(self, node_id: int) -> Sequence[ConnectivityLog]:
        """Get connectivity logs by node ID."""
        stmt = select(ConnectivityLog).where(ConnectivityLog.node_id == node_id).order_by(ConnectivityLog.started_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_node(self, node_id: int) -> Sequence[ConnectivityLog]:
        """Get active connectivity logs for a node (ended_at is NULL)."""
        stmt = select(ConnectivityLog).where(
            ConnectivityLog.node_id == node_id,
            ConnectivityLog.ended_at.is_(None)
        ).order_by(ConnectivityLog.started_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
