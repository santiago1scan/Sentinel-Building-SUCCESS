"""Desloguear el nodo: revoca en consulta y olvida la credencial local."""

import pytest

from app.datos.canales.consulta_client import ConsultaError
from app.negocio.registro_nodo import RegistroError
from app.presentacion.auth import require_user

AUTH = {"Authorization": "Bearer token-usuario"}


class ConsultaFalsa:
    configurado = True

    def __init__(self, error=None):
        self.error = error
        self.revocados = []

    def revocar_nodo(self, node_id, token):
        if self.error:
            raise self.error
        self.revocados.append((node_id, token))


@pytest.fixture
def registrado(cliente):
    """Un nodo ya registrado: credencial en SQLite y en memoria, con node_id 7."""
    contenedor = cliente.app.state.contenedor
    servicio = contenedor.registro
    servicio._repo.guardar_credencial(servicio._codigo, 7, "tok-nodo")
    servicio._aplicar(servicio._codigo, "tok-nodo", 7)
    servicio._consulta = ConsultaFalsa()
    cliente.app.dependency_overrides[require_user] = lambda: object()
    yield servicio
    cliente.app.dependency_overrides.clear()


def test_desloguear_revoca_en_consulta_y_borra_la_credencial(cliente, registrado):
    respuesta = cliente.post("/api/registro/desloguear", headers=AUTH)

    assert respuesta.status_code == 200
    assert registrado._consulta.revocados == [(7, "token-usuario")]
    cuerpo = respuesta.json()
    assert cuerpo["registrado"] is False and cuerpo["credencial_activa"] is False
    assert registrado._repo.node_ids() == {}


def test_tras_desloguear_se_puede_solicitar_un_registro_nuevo(cliente, registrado):
    cliente.post("/api/registro/desloguear", headers=AUTH)

    assert registrado._repo.tiene_credencial(registrado._codigo) is False


def test_si_consulta_no_responde_no_se_borra_nada(cliente, registrado):
    registrado._consulta = ConsultaFalsa(ConsultaError(None, "sin conexión"))

    respuesta = cliente.post("/api/registro/desloguear", headers=AUTH)

    assert respuesta.status_code == 502
    assert registrado._repo.tiene_credencial(registrado._codigo) is True
    assert registrado.estado()["credencial_activa"] is True


def test_si_el_nodo_ya_no_existe_en_consulta_se_limpia_lo_local(cliente, registrado):
    registrado._consulta = ConsultaFalsa(ConsultaError(404, "Node not found"))

    assert cliente.post("/api/registro/desloguear", headers=AUTH).status_code == 200
    assert registrado._repo.tiene_credencial(registrado._codigo) is False


@pytest.mark.parametrize("estado", [401, 403, 503])
def test_los_rechazos_de_consulta_se_pasan_tal_cual_y_no_borran(cliente, registrado, estado):
    registrado._consulta = ConsultaFalsa(ConsultaError(estado, "no"))

    assert cliente.post("/api/registro/desloguear", headers=AUTH).status_code == estado
    assert registrado._repo.tiene_credencial(registrado._codigo) is True


def test_sin_node_id_conocido_responde_409(cliente):
    servicio = cliente.app.state.contenedor.registro
    servicio._consulta = ConsultaFalsa()
    cliente.app.dependency_overrides[require_user] = lambda: object()
    try:
        assert cliente.post("/api/registro/desloguear", headers=AUTH).status_code == 409
    finally:
        cliente.app.dependency_overrides.clear()


def test_sin_sesion_no_llega_a_consulta(cliente):
    assert cliente.post("/api/registro/desloguear").status_code in (401, 503)
