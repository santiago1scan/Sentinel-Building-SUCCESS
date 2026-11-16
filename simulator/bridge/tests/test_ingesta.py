import os
import time

import pytest
from fastapi.testclient import TestClient

from app.main import crear_app
from tests.test_canales import ServidorFalso


def lectura(event_id="evt-1", node="NODE-FLOOR-1", priority="normal", sensor="accelerometer"):
    payloads = {
        "accelerometer": {"x_g": 0.1, "y_g": 0.2, "z_g": 1.0, "rms_g": 1.0, "frequency_hz": 5.0},
        "power_monitor": {"bus_voltage_v": 12.0, "current_ma": 100.0, "power_mw": 1200.0,
                          "battery_low": False},
    }
    return {
        "event_id": event_id,
        "event_type": "sensor_reading",
        "node_id": node,
        "sensor_id": f"SENSOR-{node}-{sensor}",
        "sensor_type": sensor,
        "sensor_model": "MODELO",
        "generated_at": "2026-11-16T10:00:00.000+00:00",
        "priority": priority,
        "payload": payloads.get(sensor, {}),
    }


def test_lecturas_sin_rest_ni_mqtt_salen_por_lora(cliente):
    respuesta = cliente.post("/v1/readings", json=[lectura("e1"), lectura("e2", sensor="power_monitor")])
    assert respuesta.status_code == 202
    cuerpo = respuesta.json()
    assert cuerpo["raw_inserted"] == 2
    assert cuerpo["nodes"] == 1
    assert cuerpo["rest_realtime"] == 0
    assert cuerpo["mqtt_catch_up"] == 0
    assert cuerpo["lora_summary"] == 1
    # Comportamiento heredado: LoRa no marca el agregado como enviado en el outbox.
    assert cuerpo["storage"] == {"raw_readings": 2, "pending": 1, "sent": 0}


def test_acepta_envoltura_readings(cliente):
    respuesta = cliente.post("/v1/readings", json={"readings": [lectura("e1")]})
    assert respuesta.status_code == 202


def test_lecturas_repetidas_no_se_duplican(cliente):
    cliente.post("/v1/readings", json=[lectura("e1")])
    cuerpo = cliente.post("/v1/readings", json=[lectura("e1")]).json()
    assert cuerpo["raw_inserted"] == 0
    assert cuerpo["storage"]["raw_readings"] == 1


def test_prioridad_desconocida_se_trata_como_normal(cliente):
    # Igual que bridge_service.py: cualquier prioridad que no sea high/critical es normal.
    respuesta = cliente.post("/v1/readings", json=[lectura("e1", priority="urgente")])
    assert respuesta.status_code == 202
    assert respuesta.json()["storage"]["raw_readings"] == 1


def test_nodo_desconocido_da_400_pero_la_lectura_ya_quedo_guardada(cliente):
    # Igual que bridge_service.py: las lecturas se guardan antes de agregarlas.
    respuesta = cliente.post("/v1/readings", json=[lectura("e1", node="NODE-X")])
    assert respuesta.status_code == 400
    assert "Nodo desconocido" in respuesta.json()["detail"]
    assert cliente.get("/health").json()["storage"]["raw_readings"] == 1


def test_tipo_de_sensor_desconocido_da_400_con_lectura_guardada(cliente):
    respuesta = cliente.post("/v1/readings", json=[lectura("e1", sensor="laser")])
    assert respuesta.status_code == 400
    assert cliente.get("/health").json()["storage"]["raw_readings"] == 1


def test_lectura_sin_event_id_da_400(cliente):
    datos = lectura("e1")
    del datos["event_id"]
    respuesta = cliente.post("/v1/readings", json=[datos])
    assert respuesta.status_code == 400


def test_json_invalido_da_400(cliente):
    respuesta = cliente.post("/v1/readings", content=b"{no es json",
                             headers={"Content-Type": "application/json"})
    assert respuesta.status_code == 400


def test_lista_vacia_da_400(cliente):
    respuesta = cliente.post("/v1/readings", json=[])
    assert respuesta.status_code == 400


def test_readings_que_no_es_lista_da_400(cliente):
    respuesta = cliente.post("/v1/readings", json={"readings": "nope"})
    assert respuesta.status_code == 400


def test_rest_entrega_y_marca_enviado(ajustes):
    servidor = ServidorFalso(202)
    try:
        ajustes = ajustes.model_copy(update={
            "api_url": servidor.url, "node_tokens": "NODE-FLOOR-1=tok-1"})
        with TestClient(crear_app(ajustes)) as cliente:
            cuerpo = cliente.post("/v1/readings", json=[lectura("e1")]).json()
    finally:
        servidor.cerrar()
    assert cuerpo["rest_realtime"] == 1
    assert cuerpo["lora_summary"] == 0
    assert cuerpo["storage"] == {"raw_readings": 1, "pending": 0, "sent": 1}
    assert servidor.ultima["token"] == "tok-1"
    assert servidor.ultima["body"]["delivery_status"] == "realtime"
    assert servidor.ultima["body"]["transport"] == "rest"


def test_rest_caido_cae_a_lora(ajustes):
    ajustes = ajustes.model_copy(update={
        "api_url": "http://127.0.0.1:9", "api_timeout": 1, "node_tokens": "NODE-FLOOR-1=tok"})
    with TestClient(crear_app(ajustes)) as cliente:
        cuerpo = cliente.post("/v1/readings", json=[lectura("e1")]).json()
    assert cuerpo["rest_realtime"] == 0
    assert cuerpo["lora_summary"] == 1
    assert cuerpo["storage"]["pending"] == 1


MQTT_HOST = os.getenv("SENTINEL_TEST_MQTT_HOST")


@pytest.mark.skipif(not MQTT_HOST, reason="requiere SENTINEL_TEST_MQTT_HOST")
def test_mqtt_entrega_pendiente_con_broker_real(ajustes):
    ajustes = ajustes.model_copy(update={
        "mqtt_host": MQTT_HOST,
        "mqtt_port": int(os.getenv("SENTINEL_TEST_MQTT_PORT", "1883")),
        "node_tokens": "NODE-FLOOR-1=tok-1",
    })
    with TestClient(crear_app(ajustes)) as cliente:
        limite = time.time() + 10
        while time.time() < limite:
            if cliente.get("/health").json()["mqtt_connected"].get("NODE-FLOOR-1"):
                break
            time.sleep(0.2)
        cuerpo = cliente.post("/v1/readings", json=[lectura("e1")]).json()
    assert cuerpo["mqtt_catch_up"] == 1
    assert cuerpo["lora_summary"] == 0
    assert cuerpo["storage"] == {"raw_readings": 1, "pending": 0, "sent": 1}
