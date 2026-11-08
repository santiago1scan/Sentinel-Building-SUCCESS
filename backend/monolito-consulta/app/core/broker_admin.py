"""Administración de clientes de nodo en el broker Mosquitto (plugin dynamic-security).

Cada nodo tiene un cliente MQTT en el broker: usuario = código del nodo, contraseña = su token,
y un rol que solo le permite publicar en su propio topic. Las órdenes se envían a
`$CONTROL/dynamic-security/v1` y el broker responde en `$CONTROL/dynamic-security/v1/response`.

Las funciones de construcción y análisis son puras. La clase `BrokerAdmin` es la única parte
que abre conexiones.
"""
import json
import logging
import threading
import uuid
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

CONTROL_TOPIC = "$CONTROL/dynamic-security/v1"
RESPONSE_TOPIC = "$CONTROL/dynamic-security/v1/response"
DEFAULT_TIMEOUT_SECONDS = 5.0


class BrokerAdminError(Exception):
    """El broker rechazó una orden, no respondió o la conexión falló."""


def node_role_name(node_code: str) -> str:
    return f"node-{node_code}"


def node_publish_topic(building_code: str, node_code: str) -> str:
    return f"sentinel/v1/{building_code}/{node_code}/telemetry/aggregate"


def build_create_node_commands(building_code: str, node_code: str, token: str) -> list[dict[str, Any]]:
    """Rol con permiso de publicar solo en el topic del nodo, y cliente con ese rol."""
    role = node_role_name(node_code)
    return [
        {
            "command": "createRole",
            "rolename": role,
            "acls": [{
                "acltype": "publishClientSend",
                "topic": node_publish_topic(building_code, node_code),
                "priority": 1,
                "allow": True,
            }],
        },
        {
            "command": "createClient",
            "username": node_code,
            "password": token,
            "roles": [{"rolename": role}],
        },
    ]


def build_disable_node_commands(node_code: str) -> list[dict[str, Any]]:
    """Deshabilitar el cliente impide nuevas conexiones y desconecta la sesión activa."""
    return [{"command": "disableClient", "username": node_code}]


def find_command_errors(response: dict[str, Any]) -> list[str]:
    """Errores devueltos por el broker en una respuesta de dynamic-security."""
    errors = []
    for item in response.get("responses", []):
        if "error" in item:
            errors.append(f"{item.get('command', '?')}: {item['error']}")
    return errors


class BrokerAdmin:
    """Envía órdenes de administración al broker, una conexión por operación."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        building_code: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.building_code = building_code
        self.timeout = timeout
        self._lock = threading.Lock()  # Las respuestas llegan a un topic común: una orden a la vez.

    def create_node(self, node_code: str, token: str) -> None:
        self._send(build_create_node_commands(self.building_code, node_code, token))
        logger.info("Cliente de nodo creado en el broker: %s", node_code)

    def upsert_node(self, node_code: str, token: str) -> None:
        """Crea el cliente o, si ya existe, reemplaza su contraseña. Idempotente.

        Se usa al entregar el token: si una entrega anterior no llegó al bridge, el reintento
        genera un token nuevo y debe poder reemplazar el anterior en el broker.
        """
        try:
            self._send(build_create_node_commands(self.building_code, node_code, token),
                       tolerate=("Role already exists",))
        except BrokerAdminError as exc:
            if "Client already exists" not in str(exc):
                raise
            self._send([{"command": "setClientPassword", "username": node_code, "password": token}])
        logger.info("Cliente de nodo registrado en el broker: %s", node_code)

    def disable_node(self, node_code: str) -> None:
        self._send(build_disable_node_commands(node_code))
        logger.info("Cliente de nodo deshabilitado en el broker: %s", node_code)

    def _send(self, commands: list[dict[str, Any]], tolerate: tuple[str, ...] = ()) -> None:
        with self._lock:
            done = threading.Event()
            outcome: dict[str, Any] = {}
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"sentinel-backend-admin-{uuid.uuid4().hex[:8]}",
                protocol=mqtt.MQTTv311,
            )
            client.username_pw_set(self.username, self.password)

            def on_connect(cl, userdata, flags, reason_code, properties=None):
                if reason_code.is_failure:
                    outcome["error"] = f"conexión rechazada por el broker: {reason_code}"
                    done.set()
                    return
                cl.subscribe(RESPONSE_TOPIC, qos=1)

            def on_subscribe(cl, userdata, mid, reason_codes, properties=None):
                cl.publish(CONTROL_TOPIC, json.dumps({"commands": commands}), qos=1)

            def on_message(cl, userdata, msg):
                try:
                    outcome["response"] = json.loads(msg.payload)
                except json.JSONDecodeError:
                    outcome["error"] = "respuesta no válida del broker"
                done.set()

            client.on_connect = on_connect
            client.on_subscribe = on_subscribe
            client.on_message = on_message
            try:
                client.connect_async(self.host, self.port, keepalive=30)
                client.loop_start()
                if not done.wait(self.timeout):
                    raise BrokerAdminError(f"el broker no respondió en {self.timeout}s")
            finally:
                client.loop_stop()
                client.disconnect()

            if "error" in outcome:
                raise BrokerAdminError(outcome["error"])
            errors = [e for e in find_command_errors(outcome["response"])
                      if not any(t in e for t in tolerate)]
            if errors:
                raise BrokerAdminError("; ".join(errors))
