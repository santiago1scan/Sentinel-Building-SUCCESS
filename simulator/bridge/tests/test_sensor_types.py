import pytest

from app.datos.canales.consulta_client import ConsultaError
from app.presentacion.auth import require_user

TIPO = {
    "sensor_type_id": 1, "name": "DHT22", "sampling_interval": 30, "default_unit": None,
    "normal_minimum": None, "normal_maximum": None,
    "metrics": [{"metric_id": 1, "metric_code": "temperature", "name": "Temperatura",
                 "unit": "°C", "normal_minimum": "18.0", "normal_maximum": "28.0",
                 "alarm_below": True, "alarm_above": True}],
}


class ConsultaFalsa:
    configurado = True

    def __init__(self):
        self.tokens = []

    def listar_tipos_sensor(self, token):
        self.tokens.append(token)
        return [TIPO]

    def obtener_tipo_sensor(self, sensor_type_id, token):
        self.tokens.append(token)
        if sensor_type_id != 1:
            raise ConsultaError(404, "SensorType not found")
        return TIPO


@pytest.fixture
def consulta(cliente):
    falsa = ConsultaFalsa()
    cliente.app.state.contenedor.catalogo_sensores._consulta = falsa
    cliente.app.dependency_overrides[require_user] = lambda: object()
    yield falsa
    cliente.app.dependency_overrides.clear()


AUTH = {"Authorization": "Bearer token-usuario"}


def test_lista_devuelve_tipos_con_metricas_y_reenvia_el_token(cliente, consulta):
    respuesta = cliente.get("/sensor-types", headers=AUTH)
    assert respuesta.status_code == 200
    assert respuesta.json()[0]["metrics"][0]["metric_code"] == "temperature"
    assert consulta.tokens == ["token-usuario"]


def test_detalle_de_un_tipo(cliente, consulta):
    respuesta = cliente.get("/sensor-types/1", headers=AUTH)
    assert respuesta.status_code == 200
    assert respuesta.json()["sensor_type_id"] == 1


def test_detalle_inexistente_responde_404(cliente, consulta):
    assert cliente.get("/sensor-types/99", headers=AUTH).status_code == 404


def test_sin_sesion_no_llega_a_consulta(cliente):
    assert cliente.get("/sensor-types").status_code in (401, 503)


def test_consulta_sin_configurar_responde_503(cliente, consulta):
    consulta.configurado = False
    assert cliente.get("/sensor-types", headers=AUTH).status_code == 503


def test_consulta_caida_responde_502(cliente, consulta):
    def falla(token):
        raise ConsultaError(None, "sin conexión")
    consulta.listar_tipos_sensor = falla
    assert cliente.get("/sensor-types", headers=AUTH).status_code == 502
