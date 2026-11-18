"""El registro del nodo manda sus sensores a consulta: escucha rechaza lecturas de sensores que no existen."""

import json

import pytest

from app.presentacion.auth import require_user
from tests.test_ingesta import lectura

AUTH = {"Authorization": "Bearer token-usuario"}
TIPOS = [{"sensor_type_id": 1, "name": "ADXL355"}, {"sensor_type_id": 2, "name": "BME688"}]


class ConsultaFalsa:
    configurado = True

    def __init__(self):
        self.solicitudes = []

    def listar_tipos_sensor(self, token):
        return TIPOS

    def solicitar_registro(self, codigo, nombre, building_id, zone_id, sensores=None):
        self.solicitudes.append({"code": codigo, "sensors": sensores})
        return {"registration_id": "r1", "poll_secret": "s", "expires_at": "2026-12-01T00:00:00Z"}


def con_modelo(evento, modelo, sensor):
    return {**evento, "sensor_model": modelo, "sensor_id": sensor}


@pytest.fixture
def servicio(cliente):
    registro = cliente.app.state.contenedor.registro
    registro._consulta = ConsultaFalsa()
    cliente.app.dependency_overrides[require_user] = lambda: object()
    yield registro
    cliente.app.dependency_overrides.clear()


def enviar(cliente, *eventos):
    assert cliente.post("/v1/readings", json=list(eventos)).status_code == 202


def test_detecta_los_sensores_que_ya_enviaron_lecturas_con_su_tipo(cliente, servicio):
    enviar(cliente, con_modelo(lectura("e1"), "ADXL355", "ADXL355-NODE-FLOOR-1"),
           con_modelo(lectura("e2", sensor="power_monitor"), "BME688", "BME688-NODE-FLOOR-1"))

    cuerpo = cliente.get("/api/registro/sensores", headers=AUTH).json()

    assert cuerpo["listos"] is True
    assert {(s["code"], s["sensor_type_id"]) for s in cuerpo["sensores"]} == {
        ("ADXL355-NODE-FLOOR-1", 1), ("BME688-NODE-FLOOR-1", 2)}


def test_la_solicitud_lleva_los_sensores_a_consulta(cliente, servicio):
    enviar(cliente, con_modelo(lectura("e1"), "ADXL355", "ADXL355-NODE-FLOOR-1"))

    respuesta = cliente.post("/api/registro", headers=AUTH,
                             json={"name": "Bridge 1", "building_id": 1, "zone_id": 1})

    assert respuesta.status_code == 202
    assert servicio._consulta.solicitudes == [
        {"code": "NODE-FLOOR-1", "sensors": [{"code": "ADXL355-NODE-FLOOR-1", "sensor_type_id": 1}]}]


def test_sin_lecturas_no_se_puede_solicitar_el_registro(cliente, servicio):
    respuesta = cliente.post("/api/registro", headers=AUTH,
                             json={"name": "Bridge 1", "building_id": 1, "zone_id": 1})

    assert respuesta.status_code == 409 and "sensores" in respuesta.json()["detail"]
    assert servicio._consulta.solicitudes == []


def test_un_modelo_sin_tipo_en_el_catalogo_bloquea_el_registro(cliente, servicio):
    enviar(cliente, con_modelo(lectura("e1"), "XYZ-1", "XYZ-NODE-FLOOR-1"))

    assert cliente.get("/api/registro/sensores", headers=AUTH).json()["listos"] is False
    respuesta = cliente.post("/api/registro", headers=AUTH,
                             json={"name": "Bridge 1", "building_id": 1, "zone_id": 1})

    assert respuesta.status_code == 422 and "XYZ-1" in respuesta.json()["detail"]
    assert servicio._consulta.solicitudes == []
