"""Node service."""
from collections.abc import Sequence

from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.core.security import generate_node_token, hash_token
from app.repositories.node_repository import NodeRepository
from app.schemas.connectivity_log import ConnectivityLogRead
from app.schemas.node import NodeCreate, NodeCreateResponse, NodeRead, NodeUpdate
from app.schemas.reading import ReadingRead
from app.schemas.sensor import SensorRead


class NodeService:
    def __init__(self, repository: NodeRepository):
        self.repository = repository

    async def create(self, node_in: NodeCreate) -> NodeCreateResponse:
        token = generate_node_token()
        data = node_in.model_dump()
        data["token_hash"] = hash_token(token)
        try:
            node = await self.repository.create(data)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to create node: {e}") from e
        # El token en claro solo existe en esta respuesta; no se puede recuperar después.
        return NodeCreateResponse.model_validate({**NodeRead.model_validate(node).model_dump(), "token": token})

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

    async def get_sensors(self, node_id: int) -> Sequence[SensorRead]:
        await self._ensure_exists(node_id)
        try:
            sensors = await self.repository.get_sensors(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve sensors: {e}") from e
        return [SensorRead.model_validate(s) for s in sensors]

    async def get_connectivity_logs(self, node_id: int) -> Sequence[ConnectivityLogRead]:
        await self._ensure_exists(node_id)
        try:
            logs = await self.repository.get_connectivity_logs(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve connectivity logs: {e}") from e
        return [ConnectivityLogRead.model_validate(log) for log in logs]

    async def get_received_readings(self, node_id: int) -> Sequence[ReadingRead]:
        await self._ensure_exists(node_id)
        try:
            readings = await self.repository.get_received_readings(node_id)
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to retrieve readings: {e}") from e
        return [ReadingRead.model_validate(r) for r in readings]

    async def _ensure_exists(self, node_id: int) -> None:
        if not await self.repository.get(node_id):
            raise NotFoundError(f"Node with id {node_id} not found")
