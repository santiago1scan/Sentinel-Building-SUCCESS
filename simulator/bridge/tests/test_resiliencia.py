"""Resiliencia del bridge: REST para promedios, MQTT para emergencias, sin pérdida al reconectar."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.datos.canales.mqtt_nodos import MQTT_OK
from app.datos.db import Database
from app.main import crear_app
from tests.test_canales import ServidorFalso
from tests.test_ingesta import lectura

NODO = "NODE-FLOOR-1"


class EnlaceFalso:
    """Sustituye a EnlaceMqttNodo: se puede 'cortar' y registra lo publicado."""

    def __init__(self):
        self.up = True
        self.confirma = True
        self.publicados = []

    def conectado(self):
        return self.up

    def publicar(self, payload):
        if not (self.up and self.confirma):
            return 7  # MQTT_ERR_NO_CONN
        self.publicados.append(payload)
        return MQTT_OK

    def cerrar(self):
        pass


@pytest.fixture
def servidor():
    s = ServidorFalso(202)
    yield s
    s.cerrar()


def montar(ajustes, url):
    return ajustes.model_copy(update={
        "api_url": url, "api_timeout": 1, "node_tokens": f"{NODO}=tok", "node_ids": f"{NODO}=5"})


@pytest.fixture
def app_con_enlace(ajustes, servidor):
    with TestClient(crear_app(montar(ajustes, servidor.url))) as cliente:
        enlace = EnlaceFalso()
        cliente.app.state.contenedor.enlaces[NODO] = enlace
        yield cliente, enlace, servidor


def enviar(cliente, prioridad="normal", n=1):
    return cliente.post("/v1/readings", json=[lectura(f"e{n}-{prioridad}", priority=prioridad)]).json()


def tipos(enlace):
    return [(p["delivery_status"], p["priority"]) for p in enlace.publicados]


def test_normal_va_solo_por_rest_y_no_toca_mqtt(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    cuerpo = enviar(cliente)
    assert cuerpo["rest_realtime"] == 1
    assert enlace.publicados == []
    assert cuerpo["storage"] == {"raw_readings": 1, "pending": 0, "sent": 1}


def test_emergencia_va_solo_por_mqtt_con_dos_bloques_de_contexto(app_con_enlace):
    cliente, enlace, servidor = app_con_enlace
    for i in range(3):
        enviar(cliente, n=i)  # 3 bloques normales por REST
    servidor.ultima = {}
    cuerpo = enviar(cliente, "high", n=9)

    assert servidor.ultima == {}  # la emergencia no pasó por REST
    assert cuerpo["rest_realtime"] == 0 and cuerpo["mqtt_catch_up"] == 1
    # Contexto: solo los 2 normales anteriores, luego la emergencia.
    assert tipos(enlace) == [("context", "normal"), ("context", "normal"), ("emergency", "high")]
    assert cuerpo["lora_summary"] == 0


def test_sin_mqtt_la_emergencia_queda_pendiente_y_sale_al_reconectar(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    enviar(cliente, n=1)
    enlace.up = False
    cuerpo = enviar(cliente, "critical", n=2)
    assert cuerpo["mqtt_catch_up"] == 0
    assert cuerpo["lora_summary"] == 1  # aviso de emergencia por LoRa mientras tanto
    assert cuerpo["storage"]["pending"] == 1
    assert enlace.publicados == []

    enlace.up = True  # vuelve la red; no llegan lecturas nuevas: lo saca el drenaje
    resultado = cliente.app.state.contenedor.ingesta.drenar()
    assert resultado["mqtt"] == 1
    assert tipos(enlace) == [("context", "normal"), ("emergency", "critical")]
    assert cliente.get("/health").json()["storage"]["pending"] == 0


def test_sin_puback_no_se_marca_enviado(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    enlace.confirma = False
    cuerpo = enviar(cliente, "high")
    assert cuerpo["mqtt_catch_up"] == 0
    assert cuerpo["storage"]["pending"] == 1
    enlace.confirma = True
    assert cliente.app.state.contenedor.ingesta.drenar()["mqtt"] == 1


def test_no_se_republica_lo_ya_entregado(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    enviar(cliente, n=1)
    enviar(cliente, "high", n=2)
    antes = len(enlace.publicados)
    cliente.app.state.contenedor.ingesta.drenar()
    cliente.app.state.contenedor.ingesta.drenar()
    assert len(enlace.publicados) == antes


def test_el_contexto_no_se_repite_en_la_segunda_emergencia_del_mismo_incidente(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    enviar(cliente, n=1)
    enviar(cliente, "high", n=2)
    enviar(cliente, "high", n=3)
    assert tipos(enlace) == [("context", "normal"), ("emergency", "high"), ("emergency", "high")]


def test_el_incidente_se_cierra_tras_bloques_normales_y_el_siguiente_abre_otro(app_con_enlace):
    cliente, enlace, _ = app_con_enlace
    enviar(cliente, "high", n=1)
    for i in range(3):
        enviar(cliente, n=10 + i)  # 3 normales seguidos cierran el incidente
    con = cliente.app.state.contenedor.db.con
    assert con.execute("SELECT status FROM incident").fetchall() == [("closed",)]
    enviar(cliente, "high", n=2)
    assert con.execute("SELECT status FROM incident ORDER BY id").fetchall() == [("closed",), ("open",)]


def test_rest_caido_acumula_y_el_drenaje_entrega_sin_lecturas_nuevas(ajustes, servidor):
    servidor.status = 503
    with TestClient(crear_app(montar(ajustes, servidor.url))) as cliente:
        for i in range(3):
            assert enviar(cliente, n=i)["rest_realtime"] == 0
        ingesta = cliente.app.state.contenedor.ingesta
        assert cliente.get("/health").json()["storage"] == {"raw_readings": 3, "pending": 3, "sent": 0}
        assert ingesta.drenar()["rest"] == 0  # sigue caído: nada se pierde ni se marca enviado

        servidor.status = 202  # vuelve REST
        # El backoff por bloque espera entre reintentos; se adelanta el reloj del último intento.
        cliente.app.state.contenedor.db.con.execute(
            "UPDATE aggregate_outbox SET last_attempt_at='2000-01-01T00:00:00.000+00:00'")
        assert ingesta.drenar()["rest"] == 3
        assert cliente.get("/health").json()["storage"] == {"raw_readings": 3, "pending": 0, "sent": 3}
        assert servidor.ultima["body"]["delivery_status"] == "catch_up"


def test_el_backoff_evita_reintentar_en_cada_pasada(ajustes, servidor):
    servidor.status = 503
    with TestClient(crear_app(montar(ajustes, servidor.url))) as cliente:
        enviar(cliente)
        ingesta = cliente.app.state.contenedor.ingesta
        ingesta.drenar()  # el último intento fue hace instantes: no toca reintentar
        (intentos,) = cliente.app.state.contenedor.db.con.execute(
            "SELECT attempts FROM aggregate_outbox").fetchone()
        assert intentos == 1


def test_el_outbox_sobrevive_a_un_reinicio(ajustes, servidor):
    servidor.status = 503
    config = montar(ajustes, servidor.url)
    with TestClient(crear_app(config)) as cliente:
        enviar(cliente, n=1)
    servidor.status = 202
    with TestClient(crear_app(config)) as cliente:  # mismo data_dir: bridge reiniciado
        cliente.app.state.contenedor.db.con.execute(
            "UPDATE aggregate_outbox SET last_attempt_at='2000-01-01T00:00:00.000+00:00'")
        assert cliente.app.state.contenedor.ingesta.drenar()["rest"] == 1


def test_base_anterior_se_migra_sin_perder_datos(tmp_path):
    ruta = tmp_path / "bridge_local.db"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE aggregate_outbox (
            message_uid TEXT PRIMARY KEY, generated_at TEXT NOT NULL, payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT, sent_at TEXT, response TEXT);
        INSERT INTO aggregate_outbox(message_uid, generated_at, payload_json) VALUES
            ('u1', 't', '{"priority":"high","bridges":[{"node_code":"NODE-FLOOR-1"}]}');
    """)
    con.commit()
    con.close()
    db = Database(ruta)
    try:
        assert db.con.execute(
            "SELECT priority, node_code, status FROM aggregate_outbox").fetchall() == [
            ("high", "NODE-FLOOR-1", "pending")]
    finally:
        db.close()
