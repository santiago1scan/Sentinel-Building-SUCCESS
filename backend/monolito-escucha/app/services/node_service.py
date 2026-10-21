"""Node service."""
from collections.abc import Sequence

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.repositories.node_repository import NodeRepository
from app.schemas.node import NodeCreate, NodeRead, NodeUpdate


class NodeService:
    def __init__(self, repository: NodeRepository):
        self.repository = repository

    async def create(self, node_in: NodeCreate) -> NodeRead:
        try:
            node = await self.repository.create(node_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to create node: {e}") from e
        return NodeRead.model_validate(node)

    async def get(self, node_id: int) -> NodeRead:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        return NodeRead.model_validate(node)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[NodeRead]:
        try:
            nodes = await self.repository.get_all(limit=limit, offset=offset)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve nodes: {e}") from e
        return [NodeRead.model_validate(n) for n in nodes]

    async def update(self, node_id: int, node_in: NodeUpdate) -> NodeRead:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        try:
            updated = await self.repository.update(node, node_in)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to update node: {e}") from e
        return NodeRead.model_validate(updated)

    async def delete(self, node_id: int) -> None:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        try:
            await self.repository.delete(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to delete node: {e}") from e

    async def get_by_code(self, code: str) -> NodeRead:
        node = await self.repository.get_by_code(code)
        if not node:
            raise NotFoundError(f"Node with code '{code}' not found")
        return NodeRead.model_validate(node)

    async def get_by_zone(self, zone_id: int) -> Sequence[NodeRead]:
        try:
            nodes = await self.repository.get_by_zone(zone_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve nodes: {e}") from e
        return [NodeRead.model_validate(n) for n in nodes]

    async def get_sensors(self, node_id: int) -> Sequence[NodeRead]:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        try:
            nodes = await self.repository.get_sensors(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve sensors: {e}") from e
        return [NodeRead.model_validate(n) for n in nodes]

    async def get_connectivity_logs(self, node_id: int) -> Sequence[NodeRead]:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        try:
            nodes = await self.repository.get_connectivity_logs(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve connectivity logs: {e}") from e
        return [NodeRead.model_validate(n) for n in nodes]

    async def get_received_readings(self, node_id: int) -> Sequence[NodeRead]:
        node = await self.repository.get(node_id)
        if not node:
            raise NotFoundError(f"Node with id {node_id} not found")
        try:
            nodes = await self.repository.get_received_readings(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve readings: {e}") from e
        return [NodeRead.model_validate(n) for n in nodes]
