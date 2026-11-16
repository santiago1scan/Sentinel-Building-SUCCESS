"""Qué mensajes MQTT acepta el consumidor: solo los que el nodo del topic puede reportar.

El broker autentica al nodo y limita su topic por ACL; el consumidor descarta además lo que
no coincide con el topic (topic inválido, JSON roto o bridges ajenos al nodo que publicó).
"""
import json
import threading
from types import SimpleNamespace

from app.services.mqtt_consumer_service import MQTTConsumerService
from tests.helpers import make_telemetry_payload


def topic_for(node_code: str) -> str:
    return f"sentinel/v1/SB-001/{node_code}/telemetry/aggregate"


def message(topic: str, payload) -> SimpleNamespace:
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return SimpleNamespace(topic=topic, payload=raw)


def deliver(msg) -> list:
    """Entrega el mensaje al consumidor y devuelve lo que recibió el handler."""
    received: list = []
    done = threading.Event()

    def handler(telemetry):
        received.append(telemetry)
        done.set()

    service = MQTTConsumerService()
    service.set_message_handler(handler)
    service._on_message(None, None, msg)
    done.wait(timeout=0.5)
    return received


def test_telemetry_from_the_node_of_the_topic_is_accepted():
    received = deliver(message(topic_for("NODE-FLOOR-1"), make_telemetry_payload(["NODE-FLOOR-1"])))

    assert len(received) == 1
    assert received[0].bridges[0].node_code == "NODE-FLOOR-1"


def test_telemetry_reporting_another_nodes_bridge_is_rejected():
    received = deliver(message(topic_for("NODE-FLOOR-1"), make_telemetry_payload(["NODE-FLOOR-2"])))

    assert received == []


def test_telemetry_mixing_own_and_foreign_bridges_is_rejected():
    payload = make_telemetry_payload(["NODE-FLOOR-1", "NODE-FLOOR-2"])

    assert deliver(message(topic_for("NODE-FLOOR-1"), payload)) == []


def test_message_on_a_topic_outside_the_node_namespace_is_rejected():
    payload = make_telemetry_payload(["NODE-FLOOR-1"])

    assert deliver(message("sentinel/v1/SB-001/NODE-FLOOR-1/commands", payload)) == []
    assert deliver(message("otro/topic", payload)) == []


def test_message_that_is_not_json_is_rejected():
    assert deliver(message(topic_for("NODE-FLOOR-1"), b"no es json")) == []


def test_message_of_another_type_is_ignored():
    payload = make_telemetry_payload(["NODE-FLOOR-1"])
    payload["message_type"] = "heartbeat"

    assert deliver(message(topic_for("NODE-FLOOR-1"), payload)) == []
