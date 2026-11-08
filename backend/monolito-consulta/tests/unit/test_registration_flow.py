"""Registro de nodos por solicitud: solicitud, aprobación, entrega única del token, rechazo y caducidad."""
import datetime
from types import SimpleNamespace

import pytest

from app.core.broker_admin import BrokerAdminError
from app.core.exceptions import ConflictError, GoneError, NotFoundError, ServiceUnavailableError
from app.schemas.registration import RegistrationRequest
from app.services.registration_service import RegistrationService
from app.services.registration_store import RegistrationStatus, RegistrationStore

T0 = datetime.datetime(2026, 11, 8, 12, 0, tzinfo=datetime.UTC)


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += datetime.timedelta(seconds=seconds)


EVENTS = []


class FakeSession:
    def __init__(self):
        self.flushed = 0

    async def flush(self):
        self.flushed += 1

    async def commit(self):
        EVENTS.append("db-commit")


class FakeNodes:
    def __init__(self):
        self.by_code = {}
        self.session = FakeSession()
        self.next_id = 100

    async def get_by_code(self, code):
        return self.by_code.get(code)

    async def get(self, node_id):
        return next((n for n in self.by_code.values() if n.node_id == node_id), None)

    async def create(self, data):
        self.next_id += 1
        node = SimpleNamespace(node_id=self.next_id, **data)
        self.by_code[data["code"]] = node
        return node


class FakeZones:
    def __init__(self, existing=(1,)):
        self.existing = set(existing)

    async def get(self, zone_id):
        return SimpleNamespace(zone_id=zone_id) if zone_id in self.existing else None


class FakeBroker:
    def __init__(self, fail=None):
        self.fail = fail
        self.created = []

    def upsert_node(self, code, token):
        EVENTS.append("broker-upsert")
        if self.fail:
            raise BrokerAdminError(self.fail)
        self.created.append((code, token))


def build(clock=None, broker=None, zones=None):
    EVENTS.clear()
    clock = clock or Clock()
    store = RegistrationStore(ttl_seconds=300, clock=clock)
    nodes = FakeNodes()
    service = RegistrationService(store, nodes, zones or FakeZones(), broker or FakeBroker())
    return service, store, nodes, clock


def request_body(code="NODE-FLOOR-3"):
    return RegistrationRequest(code=code, name="Bridge 3", building_code="SB-001", zone_code="ZONE-F3")


# --- Almacén: tiempo de vida y secreto ---

def test_registration_expires_after_ttl():
    clock = Clock()
    store = RegistrationStore(ttl_seconds=300, clock=clock)
    item, _ = store.create("NODE-X", "x", "SB-001", "Z")

    clock.advance(299)
    assert store.get(item.id).status == RegistrationStatus.PENDING

    clock.advance(2)
    assert store.get(item.id).status == RegistrationStatus.EXPIRED
    assert store.pending() == []


def test_poll_secret_is_verified_by_hash_only():
    store = RegistrationStore(ttl_seconds=300, clock=Clock())
    item, secret = store.create("NODE-X", "x", "SB-001", "Z")

    assert store.verify_secret(item, secret)
    assert not store.verify_secret(item, "otro-secreto")
    assert secret not in item.poll_secret_hash


# --- Solicitud ---

@pytest.mark.asyncio
async def test_request_is_pending_and_listed_for_admin():
    service, *_ = build()

    item, secret = await service.request(request_body())

    assert item.status == RegistrationStatus.PENDING
    assert [p.id for p in service.list_pending()] == [item.id]
    assert secret


@pytest.mark.asyncio
async def test_request_for_existing_node_code_is_rejected():
    service, _, nodes, _ = build()
    nodes.by_code["NODE-FLOOR-3"] = SimpleNamespace(node_id=9, code="NODE-FLOOR-3")

    with pytest.raises(ConflictError):
        await service.request(request_body())


@pytest.mark.asyncio
async def test_second_open_request_for_same_code_is_rejected():
    service, *_ = build()
    await service.request(request_body())

    with pytest.raises(ConflictError):
        await service.request(request_body())


# --- Aprobación y entrega ---

@pytest.mark.asyncio
async def test_node_does_not_exist_until_approved():
    service, _, nodes, _ = build()
    item, _ = await service.request(request_body())

    assert "NODE-FLOOR-3" not in nodes.by_code

    await service.approve(item.id, zone_id=1)
    assert "NODE-FLOOR-3" in nodes.by_code


@pytest.mark.asyncio
async def test_approve_with_unknown_zone_is_not_found():
    service, *_ = build(zones=FakeZones(existing=()))
    item, _ = await service.request(request_body())

    with pytest.raises(NotFoundError):
        await service.approve(item.id, zone_id=99)


@pytest.mark.asyncio
async def test_poll_before_approval_returns_nothing_and_no_token():
    service, *_ = build()
    item, secret = await service.request(request_body())

    assert await service.deliver(item.id, secret) is None


@pytest.mark.asyncio
async def test_token_is_delivered_once_after_approval():
    broker = FakeBroker()
    service, _, nodes, _ = build(broker=broker)
    item, secret = await service.request(request_body())
    await service.approve(item.id, zone_id=1)

    delivered = await service.deliver(item.id, secret)

    assert delivered.node_code == "NODE-FLOOR-3"
    assert broker.created == [("NODE-FLOOR-3", delivered.token)]
    # La BD se confirma antes de tocar el broker.
    assert EVENTS.index("db-commit") < EVENTS.index("broker-upsert")
    assert nodes.by_code["NODE-FLOOR-3"].token_hash is not None
    assert nodes.by_code["NODE-FLOOR-3"].token_hash != delivered.token
    with pytest.raises(GoneError):
        await service.deliver(item.id, secret)


@pytest.mark.asyncio
async def test_wrong_secret_gets_not_found_and_no_token():
    service, *_ = build()
    item, _ = await service.request(request_body())
    await service.approve(item.id, zone_id=1)

    with pytest.raises(NotFoundError):
        await service.deliver(item.id, "secreto-falso")


@pytest.mark.asyncio
async def test_broker_failure_keeps_request_approved_for_retry():
    broker = FakeBroker(fail="timeout")
    service, *_ = build(broker=broker)
    item, secret = await service.request(request_body())
    await service.approve(item.id, zone_id=1)

    with pytest.raises(ServiceUnavailableError):
        await service.deliver(item.id, secret)

    assert item.status == RegistrationStatus.APPROVED
    broker.fail = None
    retry = await service.deliver(item.id, secret)
    assert retry.node_code == "NODE-FLOOR-3"
    # El reintento genera un token nuevo: el que falló nunca llegó al bridge.
    assert broker.created[-1] == ("NODE-FLOOR-3", retry.token)


# --- Rechazo y caducidad ---

@pytest.mark.asyncio
async def test_rejected_request_never_delivers_a_token():
    broker = FakeBroker()
    service, _, nodes, _ = build(broker=broker)
    item, secret = await service.request(request_body())

    await service.reject(item.id)

    with pytest.raises(GoneError):
        await service.deliver(item.id, secret)
    assert broker.created == []
    assert "NODE-FLOOR-3" not in nodes.by_code


@pytest.mark.asyncio
async def test_expired_request_cannot_be_approved():
    clock = Clock()
    service, *_ = build(clock=clock)
    item, _ = await service.request(request_body())
    clock.advance(301)

    with pytest.raises(ConflictError):
        await service.approve(item.id, zone_id=1)


@pytest.mark.asyncio
async def test_approval_gives_bridge_a_full_ttl_to_collect_the_token():
    clock = Clock()
    service, *_ = build(clock=clock)
    item, secret = await service.request(request_body())
    clock.advance(200)
    await service.approve(item.id, zone_id=1)

    clock.advance(299)
    assert (await service.deliver(item.id, secret)).node_code == "NODE-FLOOR-3"


def test_upsert_creates_then_replaces_password_when_client_exists():
    from app.core.broker_admin import BrokerAdmin

    class Stub(BrokerAdmin):
        def __init__(self):
            super().__init__("h", 1, "u", "p", "SB-001")
            self.batches = []

        def _send(self, commands, tolerate=()):
            self.batches.append([c["command"] for c in commands])
            if commands[0]["command"] == "createRole" and len(self.batches) == 1:
                raise BrokerAdminError("createClient: Client already exists")

    stub = Stub()
    stub.upsert_node("NODE-FLOOR-3", "tok")

    assert stub.batches == [["createRole", "createClient"], ["setClientPassword"]]
