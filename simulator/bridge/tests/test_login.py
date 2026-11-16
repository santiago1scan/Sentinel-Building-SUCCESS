import pytest

from app.core.config import Settings
from app.presentacion import auth as auth_mod
from app.presentacion.routers import login as login_mod


@pytest.fixture
def firebase(monkeypatch):
    """Permite fijar la configuración de Firebase por prueba y limpia el verificador en caché."""
    def fijar(**valores):
        ajustes = Settings(**valores)
        monkeypatch.setattr(auth_mod, "get_settings", lambda: ajustes)
        monkeypatch.setattr(login_mod, "get_settings", lambda: ajustes)
        auth_mod.get_firebase_verifier.cache_clear()
    yield fijar
    auth_mod.get_firebase_verifier.cache_clear()


def test_pagina_login_se_sirve_con_el_sdk_de_firebase(cliente):
    respuesta = cliente.get("/login")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "firebasejs" in respuesta.text
    assert "signInWithPopup" in respuesta.text


def test_config_publica_sin_firebase_no_esta_configurada(cliente, firebase):
    firebase()
    cuerpo = cliente.get("/auth/config").json()
    assert cuerpo["configurado"] is False


def test_config_publica_no_expone_datos_privados(cliente, firebase):
    firebase(firebase_api_key="api-publica", firebase_project_id="proyecto-x",
             firebase_admin_emails="admin@example.com")
    cuerpo = cliente.get("/auth/config").json()
    assert cuerpo["configurado"] is True
    assert cuerpo["projectId"] == "proyecto-x"
    assert "admin@example.com" not in str(cuerpo)  # la lista de administradores no sale al navegador


def test_me_sin_firebase_configurado_responde_503(cliente, firebase):
    firebase()
    assert cliente.get("/auth/me").status_code == 503


def test_me_sin_token_responde_401(cliente, firebase):
    firebase(firebase_project_id="proyecto-x")
    assert cliente.get("/auth/me").status_code == 401


def test_me_con_token_malformado_responde_401(cliente, firebase):
    firebase(firebase_project_id="proyecto-x")
    respuesta = cliente.get("/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Invalid or expired token"


def test_panel_se_sirve_dentro_del_monolito(cliente):
    respuesta = cliente.get("/panel")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "<title>" in respuesta.text
    assert "</html>" in respuesta.text


def test_panel_enlaza_styles_css_y_se_sirve(cliente):
    assert 'href="/static/styles.css"' in cliente.get("/panel").text
    respuesta = cliente.get("/static/styles.css")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/css")
