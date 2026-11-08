"""Unit tests for MQTT credential validation and node revocation."""
from datetime import UTC, datetime

import pytest

from app.core.exceptions import UnauthorizedError
from app.services.node_auth_service import NodeAuthService
from tests.helpers import FakeNodeRepository, make_node


@pytest.mark.asyncio
async def test_mqtt_credentials_accepted_when_username_is_the_node_code():
    node = make_node("NODE-FLOOR-1")
    service = NodeAuthService(FakeNodeRepository({"valid-token": node}))

    result = await service.authenticate_mqtt("NODE-FLOOR-1", "valid-token")

    assert result is node


@pytest.mark.asyncio
async def test_mqtt_credentials_rejected_when_username_belongs_to_another_node():
    service = NodeAuthService(
        FakeNodeRepository({"token-of-floor-1": make_node("NODE-FLOOR-1")})
    )

    with pytest.raises(UnauthorizedError):
        await service.authenticate_mqtt("NODE-FLOOR-2", "token-of-floor-1")


@pytest.mark.asyncio
async def test_mqtt_credentials_rejected_for_unknown_token():
    service = NodeAuthService(FakeNodeRepository({}))

    with pytest.raises(UnauthorizedError):
        await service.authenticate_mqtt("NODE-FLOOR-1", "unknown")


@pytest.mark.asyncio
async def test_revoked_node_is_rejected_on_mqtt_and_rest_paths():
    node = make_node("NODE-FLOOR-1")
    node.revoked_at = datetime(2026, 11, 8, tzinfo=UTC)
    service = NodeAuthService(FakeNodeRepository({"valid-token": node}))

    with pytest.raises(UnauthorizedError) as mqtt_error:
        await service.authenticate_mqtt("NODE-FLOOR-1", "valid-token")
    with pytest.raises(UnauthorizedError) as rest_error:
        await service.authenticate("valid-token")

    assert mqtt_error.value.detail == "Node token revoked"
    assert rest_error.value.detail == "Node token revoked"

