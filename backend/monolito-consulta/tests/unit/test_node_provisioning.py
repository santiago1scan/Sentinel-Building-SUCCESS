"""NodeService: el alta y la revocación de un nodo también actualizan el broker."""
import datetime
import decimal
from types import SimpleNamespace

import pytest

from app.core.broker_admin import BrokerAdminError
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.schemas.node import NodeCreate
from app.services.node_service import NodeService


class FakeSession:
    def __init__(self):
        self.flushed = 0

    async def flush(self):
        self.flushed += 1


class FakeNodeRepository:
    def __init__(self, existing=None):
        self.session = FakeSession()
        self.created_data = None
        self.existing = existing

    async def create(self, data):
        self.created_data = data
        return SimpleNamespace(
            node_id=5, code=data["code"], name=data["name"], zone_id=data["zone_id"],
            ip_address=None, local_storage_mb=None,
            registered_at=datetime.datetime(2026, 11, 8, tzinfo=datetime.UTC),
        )

    async def get(self, node_id):
        return self.existing


class FakeBroker:
    def __init__(self, fail_with=None):
        self.fail_with = fail_with
        self.created = []
        self.disabled = []

    def create_node(self, node_code, token):
        if self.fail_with:
            raise BrokerAdminError(self.fail_with)
        self.created.append((node_code, token))

    def disable_node(self, node_code):
        if self.fail_with:
            raise BrokerAdminError(self.fail_with)
        self.disabled.append(node_code)


NODE_IN = NodeCreate(code="NODE-FLOOR-1", name="Bridge 1", zone_id=1)


@pytest.mark.asyncio
async def test_create_registers_node_client_with_the_returned_token():
    repo, broker = FakeNodeRepository(), FakeBroker()
    result = await NodeService(repo, broker).create(NODE_IN)

    assert broker.created == [("NODE-FLOOR-1", result.token)]
    assert result.token
    # En la BD solo se guarda el hash, nunca el token en claro.
    assert repo.created_data["token_hash"] != result.token
    assert result.token not in repo.created_data.values()


@pytest.mark.asyncio
async def test_create_fails_when_broker_rejects_the_client():
    service = NodeService(FakeNodeRepository(), FakeBroker(fail_with="Client already exists"))

    with pytest.raises(ServiceUnavailableError) as error:
        await service.create(NODE_IN)

    assert "Client already exists" in error.value.detail


@pytest.mark.asyncio
async def test_create_requires_a_configured_broker():
    service = NodeService(FakeNodeRepository(), broker=None)

    with pytest.raises(ServiceUnavailableError):
        await service.create(NODE_IN)


@pytest.mark.asyncio
async def test_revoke_disables_client_and_marks_node_revoked():
    node = SimpleNamespace(node_id=5, code="NODE-FLOOR-1", revoked_at=None)
    repo, broker = FakeNodeRepository(existing=node), FakeBroker()

    await NodeService(repo, broker).revoke(5)

    assert broker.disabled == ["NODE-FLOOR-1"]
    assert node.revoked_at is not None
    assert repo.session.flushed == 1


@pytest.mark.asyncio
async def test_revoke_keeps_node_active_when_broker_fails():
    node = SimpleNamespace(node_id=5, code="NODE-FLOOR-1", revoked_at=None)
    service = NodeService(FakeNodeRepository(existing=node), FakeBroker(fail_with="timeout"))

    with pytest.raises(ServiceUnavailableError):
        await service.revoke(5)

    assert node.revoked_at is None


@pytest.mark.asyncio
async def test_revoke_unknown_node_is_not_found_and_does_not_touch_broker():
    broker = FakeBroker()

    with pytest.raises(NotFoundError):
        await NodeService(FakeNodeRepository(existing=None), broker).revoke(99)

    assert broker.disabled == []
