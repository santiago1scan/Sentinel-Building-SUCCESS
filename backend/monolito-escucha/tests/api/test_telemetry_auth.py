"""API tests for POST /telemetry/aggregate: X-Node-Token authentication and bridge ownership.

The app is built with only the telemetry router, and the database dependencies are
replaced by fakes, so no PostgreSQL or MQTT broker is needed.
"""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.deps import get_node_repo, get_telemetry_service
from app.api.routes import telemetry
from app.core.exceptions import AppException
from tests.helpers import (
    FakeNodeRepository,
    FakeTelemetryService,
    make_node,
    make_telemetry_payload,
)

ENDPOINT = "/telemetry/aggregate"
OWN_CODE = "NODE-FLOOR-1"
FOREIGN_CODE = "NODE-FLOOR-2"
VALID_TOKEN = "token-of-floor-1"


@pytest.fixture
def telemetry_service() -> FakeTelemetryService:
    return FakeTelemetryService()


@pytest.fixture
def client(telemetry_service: FakeTelemetryService) -> TestClient:
    app = FastAPI()

    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(telemetry.router)
    app.dependency_overrides[get_node_repo] = lambda: FakeNodeRepository(
        {VALID_TOKEN: make_node(OWN_CODE)}
    )
    app.dependency_overrides[get_telemetry_service] = lambda: telemetry_service
    return TestClient(app)


def test_rejects_request_without_token_header(client, telemetry_service):
    response = client.post(ENDPOINT, json=make_telemetry_payload([OWN_CODE]))

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing X-Node-Token header"
    assert telemetry_service.calls == []


def test_rejects_empty_token_header(client, telemetry_service):
    response = client.post(
        ENDPOINT,
        json=make_telemetry_payload([OWN_CODE]),
        headers={"X-Node-Token": ""},
    )

    assert response.status_code == 401
    assert telemetry_service.calls == []


def test_rejects_unknown_token(client, telemetry_service):
    response = client.post(
        ENDPOINT,
        json=make_telemetry_payload([OWN_CODE]),
        headers={"X-Node-Token": "token-that-does-not-exist"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid node token"
    assert telemetry_service.calls == []


def test_token_in_query_string_is_not_accepted(client, telemetry_service):
    response = client.post(
        f"{ENDPOINT}?node_token={VALID_TOKEN}",
        json=make_telemetry_payload([OWN_CODE]),
    )

    assert response.status_code == 401
    assert telemetry_service.calls == []


def test_accepts_valid_token_for_own_bridge(client, telemetry_service):
    response = client.post(
        ENDPOINT,
        json=make_telemetry_payload([OWN_CODE]),
        headers={"X-Node-Token": VALID_TOKEN},
    )

    assert response.status_code == 202
    assert response.json()["message_uid"] == "msg-0001"
    assert len(telemetry_service.calls) == 1


def test_rejects_valid_token_reporting_another_bridge(client, telemetry_service):
    response = client.post(
        ENDPOINT,
        json=make_telemetry_payload([FOREIGN_CODE]),
        headers={"X-Node-Token": VALID_TOKEN},
    )

    assert response.status_code == 403
    assert telemetry_service.calls == []


def test_rejects_valid_token_when_message_mixes_own_and_foreign_bridges(
    client, telemetry_service
):
    response = client.post(
        ENDPOINT,
        json=make_telemetry_payload([OWN_CODE, FOREIGN_CODE]),
        headers={"X-Node-Token": VALID_TOKEN},
    )

    assert response.status_code == 403
    assert telemetry_service.calls == []
