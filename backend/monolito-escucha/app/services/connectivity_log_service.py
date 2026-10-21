"""ConnectivityLog service."""
from collections.abc import Sequence

from app.repositories.connectivity_log_repository import ConnectivityLogRepository
from app.schemas.connectivity_log import (
    ConnectivityLogCreate,
    ConnectivityLogRead,
    ConnectivityLogUpdate,
)


class ConnectivityLogService:
    def __init__(self, repository: ConnectivityLogRepository):
        self.repository = repository

    async def create(self, log_in: ConnectivityLogCreate) -> ConnectivityLogRead:
        log = await self.repository.create(log_in)
        return ConnectivityLogRead.model_validate(log)

    async def get(self, connectivity_id: int) -> ConnectivityLogRead | None:
        log = await self.repository.get(connectivity_id)
        return ConnectivityLogRead.model_validate(log) if log else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[ConnectivityLogRead]:
        logs = await self.repository.get_all(limit=limit, offset=offset)
        return [ConnectivityLogRead.model_validate(log) for log in logs]

    async def update(self, connectivity_id: int, log_in: ConnectivityLogUpdate) -> ConnectivityLogRead | None:
        log = await self.repository.get(connectivity_id)
        if not log:
            return None
        updated = await self.repository.update(log, log_in)
        return ConnectivityLogRead.model_validate(updated)

    async def get_by_node(self, node_id: int) -> Sequence[ConnectivityLogRead]:
        logs = await self.repository.get_by_node(node_id)
        return [ConnectivityLogRead.model_validate(log) for log in logs]

    async def get_active_by_node(self, node_id: int) -> Sequence[ConnectivityLogRead]:
        logs = await self.repository.get_active_by_node(node_id)
        return [ConnectivityLogRead.model_validate(log) for log in logs]
