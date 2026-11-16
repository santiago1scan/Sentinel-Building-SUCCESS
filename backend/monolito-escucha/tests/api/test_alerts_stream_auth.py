"""El stream de alertas exige ID token de Firebase, cerrado por omisión."""
import pytest
from fastapi.testclient import TestClient

from app.api import auth
from app.core.exceptions import UnauthorizedError
from app.main import app


@pytest.fixture(autouse=True)
def _clear_verifier_cache():
    auth.get_firebase_verifier.cache_clear()
    yield
    auth.get_firebase_verifier.cache_clear()


def test_sin_firebase_configurado_responde_503(monkeypatch):
    monkeypatch.setattr(auth.settings, "firebase_project_id", None)
    client = TestClient(app)

    response = client.get("/alerts/stream")

    assert response.status_code == 503


def test_sin_token_responde_401(monkeypatch):
    class FakeVerifier:
        def verify(self, token):
            raise UnauthorizedError("Invalid or expired token")

    monkeypatch.setattr(auth, "get_firebase_verifier", lambda: FakeVerifier())
    client = TestClient(app)

    assert client.get("/alerts/stream").status_code == 401


def test_token_invalido_en_query_responde_401(monkeypatch):
    class FakeVerifier:
        def verify(self, token):
            raise UnauthorizedError("Invalid or expired token")

    monkeypatch.setattr(auth, "get_firebase_verifier", lambda: FakeVerifier())
    client = TestClient(app)

    assert client.get("/alerts/stream", params={"access_token": "malo"}).status_code == 401


def test_atender_sin_configuracion_responde_503(monkeypatch):
    monkeypatch.setattr(auth.settings, "firebase_project_id", None)
    client = TestClient(app)

    assert client.post("/alerts/1/handle").status_code == 503
