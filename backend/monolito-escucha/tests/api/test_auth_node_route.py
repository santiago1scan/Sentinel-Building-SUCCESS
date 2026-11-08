"""API tests for POST /auth/node, the endpoint the Mosquitto auth plugin calls."""
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.deps import get_node_repo
from app.api.routes import auth
from app.core.exceptions import AppException
from tests.helpers import FakeNodeRepository, make_node

ENDPOINT = "/auth/node"
NODE_CODE = "NODE-FLOOR-1"
TOKEN = "token-of-floor-1"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(auth.router)
    app.dependency_overrides[get_node_repo] = lambda: FakeNodeRepository(
        {TOKEN: make_node(NODE_CODE)}
    )
    return TestClient(app)


def test_allows_node_with_matching_username_and_token(client):
    response = client.post(ENDPOINT, json={"username": NODE_CODE, "password": TOKEN})

    assert response.status_code == 200
    assert response.json() == {"allowed": True}


def test_rejects_unknown_token(client):
    response = client.post(ENDPOINT, json={"username": NODE_CODE, "password": "wrong"})

    assert response.status_code == 401


def test_rejects_username_that_is_not_the_token_owner(client):
    response = client.post(ENDPOINT, json={"username": "NODE-FLOOR-2", "password": TOKEN})

    assert response.status_code == 401


def test_rejects_missing_password(client):
    response = client.post(ENDPOINT, json={"username": NODE_CODE})

    assert response.status_code == 422


def test_rejects_empty_password(client):
    response = client.post(ENDPOINT, json={"username": NODE_CODE, "password": ""})

    assert response.status_code == 422
