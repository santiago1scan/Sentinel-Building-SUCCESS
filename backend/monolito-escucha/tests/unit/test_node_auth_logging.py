"""Los rechazos de autenticación de un nodo quedan registrados, sin exponer el token."""
import logging
from datetime import UTC, datetime

import pytest

from app.core.exceptions import UnauthorizedError
from app.services.node_auth_service import NodeAuthService
from tests.helpers import FakeNodeRepository, make_node

LOGGER = "app.services.node_auth_service"


@pytest.mark.asyncio
async def test_unknown_token_rejection_is_logged_without_the_token(caplog):
    service = NodeAuthService(FakeNodeRepository({}))

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        with pytest.raises(UnauthorizedError):
            await service.authenticate("secret-token-123")

    assert any("token desconocido" in r.getMessage() for r in caplog.records)
    assert "secret-token-123" not in caplog.text


@pytest.mark.asyncio
async def test_revoked_token_rejection_is_logged_with_the_node_code(caplog):
    node = make_node("NODE-FLOOR-1")
    node.revoked_at = datetime(2026, 11, 8, tzinfo=UTC)
    service = NodeAuthService(FakeNodeRepository({"revoked-token-456": node}))

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        with pytest.raises(UnauthorizedError):
            await service.authenticate("revoked-token-456")

    assert any("NODE-FLOOR-1" in r.getMessage() and "revocada" in r.getMessage() for r in caplog.records)
    assert "revoked-token-456" not in caplog.text


@pytest.mark.asyncio
async def test_accepted_token_is_not_logged_as_a_rejection(caplog):
    service = NodeAuthService(FakeNodeRepository({"good-token": make_node("NODE-FLOOR-1")}))

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        await service.authenticate("good-token")

    assert caplog.records == []
