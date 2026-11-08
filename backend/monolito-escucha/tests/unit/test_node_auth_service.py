"""Unit tests for NodeAuthService: token authentication and bridge ownership."""
import pytest

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import hash_token
from app.services.node_auth_service import NodeAuthService
from tests.helpers import FakeNodeRepository, make_node


@pytest.mark.asyncio
async def test_authenticate_returns_node_for_valid_token():
    node = make_node("NODE-FLOOR-1")
    service = NodeAuthService(FakeNodeRepository({"valid-token": node}))

    result = await service.authenticate("valid-token")

    assert result is node


@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_token():
    service = NodeAuthService(FakeNodeRepository({"valid-token": make_node()}))

    with pytest.raises(UnauthorizedError) as exc_info:
        await service.authenticate("wrong-token")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_rejects_empty_token():
    service = NodeAuthService(FakeNodeRepository({"valid-token": make_node()}))

    with pytest.raises(UnauthorizedError):
        await service.authenticate("")


@pytest.mark.asyncio
async def test_authenticate_looks_up_the_hash_never_the_plain_token():
    repo = FakeNodeRepository({"valid-token": make_node()})
    service = NodeAuthService(repo)

    await service.authenticate("valid-token")

    assert repo.requested_hashes == [hash_token("valid-token")]
    assert "valid-token" not in repo.requested_hashes


@pytest.mark.asyncio
async def test_authenticate_does_not_match_token_of_another_node():
    service = NodeAuthService(
        FakeNodeRepository({"token-node-a": make_node("NODE-A", node_id=1)})
    )

    with pytest.raises(UnauthorizedError):
        await service.authenticate("token-node-b")


def test_ensure_owns_bridges_allows_the_authenticated_node():
    node = make_node("NODE-FLOOR-1")

    NodeAuthService.ensure_owns_bridges(node, ["NODE-FLOOR-1"])


def test_ensure_owns_bridges_allows_repeated_own_code():
    node = make_node("NODE-FLOOR-1")

    NodeAuthService.ensure_owns_bridges(node, ["NODE-FLOOR-1", "NODE-FLOOR-1"])


def test_ensure_owns_bridges_rejects_another_bridge():
    node = make_node("NODE-FLOOR-1")

    with pytest.raises(ForbiddenError) as exc_info:
        NodeAuthService.ensure_owns_bridges(node, ["NODE-FLOOR-2"])

    assert exc_info.value.status_code == 403


def test_ensure_owns_bridges_rejects_mix_of_own_and_foreign_bridges():
    node = make_node("NODE-FLOOR-1")

    with pytest.raises(ForbiddenError):
        NodeAuthService.ensure_owns_bridges(node, ["NODE-FLOOR-1", "NODE-FLOOR-2"])
