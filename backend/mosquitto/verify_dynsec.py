"""Verifica el broker con dynamic-security: autenticación, ACL por nodo y revocación.

Crea clientes y roles con nombres VERIFY-* (no toca nodos reales) y los borra al terminar.

    MQTT_ADMIN_PASSWORD=... python verify_dynsec.py [--host localhost] [--port 1883]

Requiere paho-mqtt (pip install "paho-mqtt>=2.1,<3").
"""
import argparse
import json
import os
import sys
import threading
import time
import uuid

import paho.mqtt.client as mqtt

BUILDING = "SB-001"
NODE_A, NODE_B, CONSUMER = "VERIFY-NODE-A", "VERIFY-NODE-B", "VERIFY-CONSUMER"
TOKEN_A, TOKEN_B, CONSUMER_PW = "verify-token-a", "verify-token-b", "verify-consumer-pw"
TOPIC_A = f"sentinel/v1/{BUILDING}/{NODE_A}/telemetry/aggregate"
TOPIC_B = f"sentinel/v1/{BUILDING}/{NODE_B}/telemetry/aggregate"
CONTROL = "$CONTROL/dynamic-security/v1"
RESPONSE = "$CONTROL/dynamic-security/v1/response"


def connect(host, port, user=None, pw=None):
    """Conecta y devuelve (cliente, resultado_booleano). El resultado sale del CONNACK real."""
    box = {}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"verify-{uuid.uuid4().hex[:6]}",
                         protocol=mqtt.MQTTv311)
    if user is not None:
        client.username_pw_set(user, pw)
    client.on_connect = lambda cl, ud, f, rc, props=None: box.update(ok=not rc.is_failure)
    client.connect_async(host, port, keepalive=30)
    client.loop_start()
    deadline = time.time() + 5
    while "ok" not in box and time.time() < deadline:
        time.sleep(0.05)
    return client, box.get("ok", False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()
    admin_pw = os.getenv("MQTT_ADMIN_PASSWORD")
    if not admin_pw:
        print("Define MQTT_ADMIN_PASSWORD", file=sys.stderr)
        return 2

    results: list[tuple[str, bool]] = []

    def check(name, ok):
        results.append((name, bool(ok)))
        print(("PASS " if ok else "FAIL ") + name)

    admin, admin_ok = connect(args.host, args.port, "admin", admin_pw)
    check("cuenta admin autentica", admin_ok)
    if not admin_ok:
        return 1

    replies: list[dict] = []
    lock = threading.Lock()

    def on_reply(cl, ud, msg):
        with lock:
            replies.append(json.loads(msg.payload))

    admin.on_message = on_reply
    admin.subscribe(RESPONSE, qos=1)
    time.sleep(0.5)

    def command(cmds):
        before = len(replies)
        admin.publish(CONTROL, json.dumps({"commands": cmds}), qos=1)
        deadline = time.time() + 5
        while len(replies) <= before and time.time() < deadline:
            time.sleep(0.05)
        out = replies[before] if len(replies) > before else {"responses": []}
        return [x["error"] for x in out.get("responses", []) if "error" in x]

    errors = command([
        {"command": "createRole", "rolename": "VERIFY-role-a", "acls": [
            {"acltype": "publishClientSend", "topic": TOPIC_A, "priority": 1, "allow": True}]},
        {"command": "createRole", "rolename": "VERIFY-role-b", "acls": [
            {"acltype": "publishClientSend", "topic": TOPIC_B, "priority": 1, "allow": True}]},
        {"command": "createRole", "rolename": "VERIFY-consumer", "acls": [
            {"acltype": "subscribePattern", "topic": f"sentinel/v1/+/+/telemetry/aggregate",
             "priority": 1, "allow": True}]},
        {"command": "createClient", "username": NODE_A, "password": TOKEN_A,
         "roles": [{"rolename": "VERIFY-role-a"}]},
        {"command": "createClient", "username": NODE_B, "password": TOKEN_B,
         "roles": [{"rolename": "VERIFY-role-b"}]},
        {"command": "createClient", "username": CONSUMER, "password": CONSUMER_PW,
         "roles": [{"rolename": "VERIFY-consumer"}]},
    ])
    check("alta de clientes y roles sin error", not errors)

    received: list[str] = []
    consumer, consumer_ok = connect(args.host, args.port, CONSUMER, CONSUMER_PW)
    consumer.on_message = lambda cl, ud, m: received.append(m.topic)
    check("consumidor conecta", consumer_ok)
    consumer.subscribe(f"sentinel/v1/+/+/telemetry/aggregate", qos=1)
    time.sleep(0.5)

    node_a, ok_a = connect(args.host, args.port, NODE_A, TOKEN_A)
    check("nodo A conecta con su token", ok_a)
    node_b, ok_b = connect(args.host, args.port, NODE_B, TOKEN_B)
    check("nodo B conecta con su token", ok_b)
    _, bad_ok = connect(args.host, args.port, NODE_A, "token-incorrecto")
    check("token incorrecto rechazado", not bad_ok)
    _, anon_ok = connect(args.host, args.port)
    check("conexión anónima rechazada", not anon_ok)

    node_a.publish(TOPIC_A, "{}", qos=1)
    node_b.publish(TOPIC_B, "{}", qos=1)
    time.sleep(1.5)
    check("nodo A entrega en su topic", received.count(TOPIC_A) == 1)
    check("nodo B entrega en su topic", received.count(TOPIC_B) == 1)

    # Cruce: el nodo A intenta publicar en el topic de B; el consumidor no debe recibirlo.
    node_a.publish(TOPIC_B, "{}", qos=1)
    time.sleep(1.5)
    check("nodo A no entrega en el topic de B", received.count(TOPIC_B) == 1)

    errors = command([{"command": "disableClient", "username": NODE_A}])
    check("revocación (disableClient) sin error", not errors)
    time.sleep(1.5)
    check("sesión activa del nodo A cortada", not node_a.is_connected())
    _, again_ok = connect(args.host, args.port, NODE_A, TOKEN_A)
    check("nodo A no vuelve a entrar tras revocar", not again_ok)

    # Limpieza: solo recursos VERIFY-*.
    command([
        {"command": "deleteClient", "username": NODE_A},
        {"command": "deleteClient", "username": NODE_B},
        {"command": "deleteClient", "username": CONSUMER},
        {"command": "deleteRole", "rolename": "VERIFY-role-a"},
        {"command": "deleteRole", "rolename": "VERIFY-role-b"},
        {"command": "deleteRole", "rolename": "VERIFY-consumer"},
    ])
    for c in (admin, consumer, node_a, node_b):
        c.loop_stop()
        c.disconnect()

    passed = sum(ok for _, ok in results)
    print(f"\n{passed}/{len(results)} checks ok")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
