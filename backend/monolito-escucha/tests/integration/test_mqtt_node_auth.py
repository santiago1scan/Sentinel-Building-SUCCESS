"""Autenticación de nodos en el broker MQTT real (dynamic-security): US17, parte MQTT.

Se ejecuta contra un broker ya levantado y crea clientes TEST-* que borra al terminar.

    INTEGRATION_MQTT_HOST=localhost INTEGRATION_MQTT_PORT=8883 \\
    INTEGRATION_MQTT_CAFILE=../mosquitto/certs/ca.crt MQTT_ADMIN_PASSWORD=... \\
    pytest tests/integration/test_mqtt_node_auth.py -v

Sin INTEGRATION_MQTT_HOST las pruebas se omiten. Sin INTEGRATION_MQTT_CAFILE se conecta en claro.
"""
import json
import os
import ssl
import time
import uuid

import paho.mqtt.client as mqtt
import pytest

HOST = os.getenv("INTEGRATION_MQTT_HOST")
PORT = int(os.getenv("INTEGRATION_MQTT_PORT", "8883"))
CAFILE = os.getenv("INTEGRATION_MQTT_CAFILE")
ADMIN_USER = os.getenv("MQTT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("MQTT_ADMIN_PASSWORD")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (HOST and ADMIN_PASSWORD),
        reason="Define INTEGRATION_MQTT_HOST y MQTT_ADMIN_PASSWORD para probar contra el broker",
    ),
]

BUILDING = "SB-001"
CONTROL = "$CONTROL/dynamic-security/v1"
RESPONSE = f"{CONTROL}/response"
SUBSCRIPTION = f"sentinel/v1/+/+/telemetry/aggregate"


def topic_for(node_code: str) -> str:
    return f"sentinel/v1/{BUILDING}/{node_code}/telemetry/aggregate"


def connect(user=None, password=None):
    """Conecta y devuelve (cliente, aceptada). `aceptada` sale del CONNACK real del broker."""
    box: dict = {}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"it-{uuid.uuid4().hex[:8]}",
                         protocol=mqtt.MQTTv311)
    if user is not None:
        client.username_pw_set(user, password)
    if CAFILE:
        client.tls_set(ca_certs=CAFILE, cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = lambda cl, ud, flags, rc, props=None: box.update(ok=not rc.is_failure)
    client.connect_async(HOST, PORT, keepalive=30)
    client.loop_start()
    deadline = time.time() + 5
    while "ok" not in box and time.time() < deadline:
        time.sleep(0.05)
    return client, box.get("ok", False)


def stop(*clients):
    for c in clients:
        c.loop_stop()
        c.disconnect()


class Broker:
    """Administra el broker como lo hace el backend de consulta: nodos con su rol y su topic."""

    def __init__(self):
        self.admin, ok = connect(ADMIN_USER, ADMIN_PASSWORD)
        assert ok, "la cuenta admin no autentica: revisa MQTT_ADMIN_PASSWORD y el puerto"
        self.replies: list[dict] = []
        self.admin.on_message = lambda cl, ud, msg: self.replies.append(json.loads(msg.payload))
        self.admin.subscribe(RESPONSE, qos=1)
        time.sleep(0.5)
        self.created: list[tuple[str, str]] = []  # (cliente, rol)

    def command(self, commands: list[dict]) -> list[str]:
        before = len(self.replies)
        self.admin.publish(CONTROL, json.dumps({"commands": commands}), qos=1)
        deadline = time.time() + 5
        while len(self.replies) <= before and time.time() < deadline:
            time.sleep(0.05)
        reply = self.replies[before] if len(self.replies) > before else {"responses": []}
        return [item["error"] for item in reply.get("responses", []) if "error" in item]

    def create_node(self, code: str, token: str) -> None:
        role = f"role-{code}"
        errors = self.command([
            {"command": "createRole", "rolename": role, "acls": [
                {"acltype": "publishClientSend", "topic": topic_for(code), "priority": 1, "allow": True}]},
            {"command": "createClient", "username": code, "password": token, "roles": [{"rolename": role}]},
        ])
        assert not errors, errors
        self.created.append((code, role))

    def create_consumer(self, username: str, password: str) -> None:
        role = f"role-{username}"
        errors = self.command([
            {"command": "createRole", "rolename": role, "acls": [
                {"acltype": "subscribePattern", "topic": SUBSCRIPTION, "priority": 1, "allow": True}]},
            {"command": "createClient", "username": username, "password": password,
             "roles": [{"rolename": role}]},
        ])
        assert not errors, errors
        self.created.append((username, role))

    def revoke(self, code: str) -> None:
        assert not self.command([{"command": "disableClient", "username": code}])

    def cleanup(self) -> None:
        for client, role in self.created:
            self.command([{"command": "deleteClient", "username": client},
                          {"command": "deleteRole", "rolename": role}])
        stop(self.admin)


@pytest.fixture
def broker():
    b = Broker()
    yield b
    b.cleanup()


@pytest.fixture
def telemetry_listener(broker):
    """Consumidor autorizado que anota los topics en los que recibe mensajes."""
    name, password = f"TEST-CONSUMER-{uuid.uuid4().hex[:6]}", "consumer-pw-it"
    broker.create_consumer(name, password)
    received: list[str] = []
    client, ok = connect(name, password)
    assert ok
    client.on_message = lambda cl, ud, msg: received.append(msg.topic)
    client.subscribe(SUBSCRIPTION, qos=1)
    time.sleep(0.5)
    yield received
    stop(client)


@pytest.fixture
def node(broker):
    code, token = f"TEST-NODE-{uuid.uuid4().hex[:6]}", f"tok-{uuid.uuid4().hex}"
    broker.create_node(code, token)
    return code, token


def test_node_with_valid_credential_connects_and_telemetry_is_accepted(node, telemetry_listener):
    """SCRUM-113."""
    code, token = node
    client, ok = connect(code, token)

    assert ok
    client.publish(topic_for(code), "{}", qos=1)
    time.sleep(1.5)
    stop(client)
    assert telemetry_listener.count(topic_for(code)) == 1


def test_node_with_wrong_token_is_rejected(node):
    """SCRUM-114: credencial inválida. El broker registra `not authorised` (el CI lo comprueba)."""
    code, _ = node
    client, ok = connect(code, "token-incorrecto")
    stop(client)

    assert not ok


def test_revoked_node_loses_its_session_and_cannot_come_back(broker, node):
    """SCRUM-114: credencial revocada."""
    code, token = node
    client, ok = connect(code, token)
    assert ok

    broker.revoke(code)
    time.sleep(1.5)

    assert not client.is_connected()
    stop(client)
    again, ok_again = connect(code, token)
    stop(again)
    assert not ok_again


def test_connection_without_credential_is_rejected():
    """SCRUM-115."""
    client, ok = connect()
    stop(client)

    assert not ok


def test_message_from_a_client_without_credential_is_not_delivered(node, telemetry_listener):
    """SCRUM-116: el broker no entrega nada de quien no se autentica."""
    code, _ = node
    client, ok = connect()
    if ok:  # Si algún día conectara, aun así no debe entregar.
        client.publish(topic_for(code), "{}", qos=1)
        time.sleep(1.5)
    stop(client)

    assert not ok
    assert telemetry_listener.count(topic_for(code)) == 0


def test_node_cannot_publish_on_another_nodes_topic(broker, node, telemetry_listener):
    """SCRUM-116: un nodo autenticado solo publica en su topic."""
    code, token = node
    other = f"TEST-NODE-{uuid.uuid4().hex[:6]}"
    broker.create_node(other, f"tok-{uuid.uuid4().hex}")
    client, ok = connect(code, token)
    assert ok

    client.publish(topic_for(other), "{}", qos=1)
    time.sleep(1.5)
    stop(client)

    assert telemetry_listener.count(topic_for(other)) == 0
