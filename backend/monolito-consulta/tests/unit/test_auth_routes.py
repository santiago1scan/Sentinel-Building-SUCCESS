"""Las rutas de administración exigen el ID token de Firebase; las del bridge siguen abiertas."""
import pytest
from fastapi.testclient import TestClient

import app.api.auth as auth
from app.api.deps import get_registration_service
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.firebase_auth import FirebaseUser
from app.main import app

ADMIN_USER = FirebaseUser(uid="uid-1", email="admin@example.com", email_verified=True)

# (método, ruta) de administración. Sin token deben responder 401 antes de tocar la base de datos.
PROTECTED = [
    ("GET", "/buildings"), ("POST", "/buildings"), ("GET", "/zones"), ("GET", "/nodes"),
    ("POST", "/nodes/1/revoke"), ("GET", "/sensors"), ("GET", "/sensor-types"),
    ("GET", "/readings"), ("GET", "/alerts"), ("GET", "/connectivity-logs"),
    ("GET", "/app-users"), ("GET", "/app-roles"),
    ("GET", "/registrations/pending"), ("GET", "/registrations/stream"),
    ("POST", "/registrations/abc/approve"), ("POST", "/registrations/abc/reject"),
]


class FakeVerifier:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.tokens: list[str] = []

    def verify(self, token):
        self.tokens.append(token)
        if isinstance(self.behaviour, Exception):
            raise self.behaviour
        return self.behaviour


class StubRegistrationService:
    def __init__(self):
        self.approved = []

    def list_pending(self):
        return []

    async def approve(self, registration_id, zone_id):
        self.approved.append((registration_id, zone_id))
        raise UnauthorizedError("no debería llegar aquí sin token")

    async def deliver(self, registration_id, poll_secret):
        return None


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def stub_service():
    service = StubRegistrationService()
    app.dependency_overrides[get_registration_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_registration_service, None)


def configure(monkeypatch, behaviour) -> FakeVerifier | None:
    verifier = None if behaviour is None else FakeVerifier(behaviour)
    monkeypatch.setattr(auth, "get_firebase_verifier", lambda: verifier)
    return verifier


@pytest.mark.parametrize("method,path", PROTECTED)
def test_admin_routes_reject_requests_without_a_token(client, monkeypatch, method, path):
    configure(monkeypatch, ADMIN_USER)

    response = client.request(method, path)

    assert response.status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED)
def test_admin_routes_are_closed_when_firebase_is_not_configured(client, monkeypatch, method, path):
    configure(monkeypatch, None)

    response = client.request(method, path, headers={"Authorization": "Bearer cualquiera"})

    assert response.status_code == 503


def test_invalid_token_is_rejected(client, monkeypatch):
    configure(monkeypatch, UnauthorizedError("Invalid or expired token"))

    response = client.get("/nodes", headers={"Authorization": "Bearer malo"})

    assert response.status_code == 401


def test_authenticated_user_outside_the_allowlist_gets_403(client, monkeypatch):
    configure(monkeypatch, ForbiddenError("User is not allowed to use this panel"))

    response = client.get("/nodes", headers={"Authorization": "Bearer valido-pero-ajeno"})

    assert response.status_code == 403


def test_non_bearer_scheme_is_rejected(client, monkeypatch):
    verifier = configure(monkeypatch, ADMIN_USER)

    response = client.get("/nodes", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401
    assert verifier.tokens == []


def test_valid_token_reaches_the_route_and_is_verified(client, monkeypatch, stub_service):
    verifier = configure(monkeypatch, ADMIN_USER)

    response = client.get("/registrations/pending", headers={"Authorization": "Bearer token-valido"})

    assert response.status_code == 200
    assert response.json() == []
    assert verifier.tokens == ["token-valido"]


def test_approve_without_token_never_reaches_the_service(client, monkeypatch, stub_service):
    configure(monkeypatch, ADMIN_USER)

    response = client.post("/registrations/abc/approve", json={"zone_id": 1})

    assert response.status_code == 401
    assert stub_service.approved == []


def test_bridge_can_request_a_registration_without_a_token(client, monkeypatch):
    configure(monkeypatch, ADMIN_USER)
    accepted = {}

    class Service(StubRegistrationService):
        async def request(self, body):
            from datetime import UTC, datetime
            from types import SimpleNamespace
            accepted["code"] = body.code
            item = SimpleNamespace(id="rid", expires_at=datetime.now(UTC))
            return item, "secret"

    app.dependency_overrides[get_registration_service] = lambda: Service()
    try:
        response = client.post("/registrations", json={
            "code": "NODE-1", "name": "Nodo", "building_code": "SB-001", "zone_code": "Z1"})
    finally:
        app.dependency_overrides.pop(get_registration_service, None)

    assert response.status_code == 202
    assert accepted["code"] == "NODE-1"


def test_bridge_can_poll_with_its_poll_secret_and_no_token(client, monkeypatch, stub_service):
    configure(monkeypatch, ADMIN_USER)

    response = client.get("/registrations/abc", headers={"X-Poll-Secret": "secreto"})

    assert response.status_code == 202


def test_root_is_open(client):
    assert client.get("/").status_code == 200


@pytest.mark.asyncio
async def test_stream_accepts_the_token_in_the_query_string(monkeypatch):
    verifier = configure(monkeypatch, ADMIN_USER)

    user = await auth.require_user_or_query_token(credentials=None, access_token="token-query")

    assert user == ADMIN_USER
    assert verifier.tokens == ["token-query"]


@pytest.mark.asyncio
async def test_header_takes_precedence_over_the_query_token(monkeypatch):
    from fastapi.security import HTTPAuthorizationCredentials
    verifier = configure(monkeypatch, ADMIN_USER)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token-header")

    await auth.require_user_or_query_token(credentials=creds, access_token="token-query")

    assert verifier.tokens == ["token-header"]


@pytest.mark.asyncio
async def test_stream_without_any_token_is_rejected(monkeypatch):
    configure(monkeypatch, ADMIN_USER)

    with pytest.raises(UnauthorizedError):
        await auth.require_user_or_query_token(credentials=None, access_token=None)


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE", "PUT"])
def test_cors_preflight_is_open_for_any_origin_and_method(client, method):
    response = client.options("/nodes", headers={
        "Origin": "https://cualquier-origen.example",
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "authorization,content-type,x-poll-secret",
    })

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert method in response.headers["access-control-allow-methods"]
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "x-poll-secret" in allowed


def test_cors_headers_are_present_on_normal_responses(client):
    response = client.get("/", headers={"Origin": "https://cualquier-origen.example"})

    assert response.headers["access-control-allow-origin"] == "*"
