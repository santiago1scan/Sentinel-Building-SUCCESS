"""Revocación de nodos: el token de un nodo revocado deja de autenticar en REST.

La autenticación MQTT la hace el broker (plugin dynamic-security), no este servicio.
"""
from datetime import UTC, datetime

import pytest

from app.core.exceptions import UnauthorizedError
from app.services.node_auth_service import NodeAuthService
from tests.helpers import FakeNodeRepository, make_node


@pytest.mark.asyncio
async def test_revoked_node_token_is_rejected():
    node = make_node("NODE-FLOOR-1")
    node.revoked_at = datetime(2026, 11, 8, tzinfo=UTC)
    service = NodeAuthService(FakeNodeRepository({"valid-token": node}))

    with pytest.raises(UnauthorizedError) as error:
        await service.authenticate("valid-token")

    assert error.value.detail == "Node token revoked"


@pytest.mark.asyncio
async def test_active_node_token_is_accepted():
    node = make_node("NODE-FLOOR-1")
    service = NodeAuthService(FakeNodeRepository({"valid-token": node}))

    assert await service.authenticate("valid-token") is node
