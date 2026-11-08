"""Node authentication service - Validates the token that identifies a sensor node."""
import logging
from collections.abc import Iterable

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import hash_token
from app.models.node import Node
from app.repositories.node_repository import NodeRepository

logger = logging.getLogger(__name__)


class NodeAuthService:
    def __init__(self, node_repo: NodeRepository):
        self.node_repo = node_repo

    async def authenticate(self, token: str) -> Node:
        """Return the active node that owns the token, or raise UnauthorizedError.

        El token nunca se registra en logs: solo el hecho del rechazo.
        """
        node = await self.node_repo.get_by_token_hash(hash_token(token))
        if node is None:
            logger.warning("Rechazo de autenticación de nodo: token desconocido")
            raise UnauthorizedError("Invalid node token")
        if node.revoked_at is not None:
            logger.warning(f"Rechazo de autenticación de nodo {node.code}: credencial revocada")
            raise UnauthorizedError("Node token revoked")
        return node

    async def authenticate_mqtt(self, username: str, token: str) -> Node:
        """Validate broker credentials: the MQTT username must be the node that owns the token."""
        node = await self.authenticate(token)
        if node.code != username:
            logger.warning(f"Rechazo MQTT: usuario '{username}' no corresponde al token del nodo {node.code}")
            raise UnauthorizedError("Username does not match node token")
        return node

    @staticmethod
    def ensure_owns_bridges(node: Node, bridge_codes: Iterable[str]) -> None:
        """A node may only report telemetry for itself, never for another bridge."""
        if any(code != node.code for code in bridge_codes):
            raise ForbiddenError("Token does not allow reporting telemetry for this bridge")
