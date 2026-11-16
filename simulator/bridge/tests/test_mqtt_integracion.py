"""Pruebas contra un broker Mosquitto real.

Solo corren si SENTINEL_TEST_MQTT_HOST apunta a un broker. Ejemplo:
    docker run --rm --network <red> -e SENTINEL_TEST_MQTT_HOST=mqtt-test <imagen> pytest -q
"""

import json
import os
import queue
import time

import paho.mqtt.client as mqtt
import pytest

from app.datos.canales.mqtt_nodos import EnlaceMqttNodo, topico_nodo

HOST = os.getenv("SENTINEL_TEST_MQTT_HOST")
PORT = int(os.getenv("SENTINEL_TEST_MQTT_PORT", "1883"))
pytestmark = pytest.mark.skipif(not HOST, reason="requiere SENTINEL_TEST_MQTT_HOST")


def esperar(condicion, segundos=10):
    limite = time.time() + segundos
    while time.time() < limite:
        if condicion():
            return True
        time.sleep(0.1)
    return False


def test_publica_en_el_topico_del_nodo_y_llega_al_suscriptor():
    recibidos: queue.Queue = queue.Queue()
    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-sub")
    sub.on_message = lambda c, u, msg: recibidos.put((msg.topic, json.loads(msg.payload)))
    sub.connect(HOST, PORT)
    topico = topico_nodo("SB-001", "NODE-FLOOR-1")
    sub.subscribe(topico, qos=1)
    sub.loop_start()

    enlace = EnlaceMqttNodo(nodo="NODE-FLOOR-1", token="t", topico=topico, host=HOST, port=PORT)
    try:
        assert esperar(enlace.conectado)
        assert enlace.publicar({"message_uid": "u1"}) == mqtt.MQTT_ERR_SUCCESS
        topic, payload = recibidos.get(timeout=10)
        assert topic == topico
        assert payload == {"message_uid": "u1"}
    finally:
        enlace.cerrar()
        sub.loop_stop()
        sub.disconnect()


def test_no_conectado_sin_broker():
    enlace = EnlaceMqttNodo(nodo="NODE-X", token="t", topico="x", host="127.0.0.1", port=9)
    try:
        time.sleep(1)
        assert enlace.conectado() is False
    finally:
        enlace.cerrar()
