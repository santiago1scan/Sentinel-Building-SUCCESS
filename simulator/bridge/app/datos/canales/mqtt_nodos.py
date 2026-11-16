"""Conexión MQTT por nodo: el broker ve la identidad del nodo, no la del bridge."""

import json
import ssl
from typing import Any

import paho.mqtt.client as mqtt


def topico_nodo(codigo_edificio: str, codigo_nodo: str) -> str:
    return f"sentinel/v1/{codigo_edificio}/{codigo_nodo}/telemetry/aggregate"


class EnlaceMqttNodo:
    def __init__(self, *, nodo: str, token: str, topico: str, host: str, port: int,
                 tls: bool = False, ca_file: str | None = None, keepalive: int = 30) -> None:
        self.nodo = nodo
        self.topico = topico
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sentinel-bridge-{nodo.lower()}",
        )
        self._client.username_pw_set(nodo, token)
        if tls:
            self._client.tls_set(ca_certs=ca_file, cert_reqs=ssl.CERT_REQUIRED)
        self._client.reconnect_delay_set(min_delay=1, max_delay=15)
        # connect_async + loop_start: paho reintenta sola si el broker no responde al arrancar.
        self._client.connect_async(host, port, keepalive=keepalive)
        self._client.loop_start()

    def conectado(self) -> bool:
        return self._client.is_connected()

    def publicar(self, payload: dict[str, Any]) -> int:
        """Devuelve el código rc de paho (mqtt.MQTT_ERR_SUCCESS si se aceptó)."""
        resultado = self._client.publish(
            self.topico, json.dumps(payload, ensure_ascii=False), qos=1, retain=False)
        return resultado.rc

    def cerrar(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
