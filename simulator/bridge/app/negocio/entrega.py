"""Decide por qué canal sale cada agregado.

Orden (igual que bridge_service.py): REST en tiempo real; MQTT para lo pendiente
(por nodo); LoRa solo como resumen cuando no hubo entrega por REST ni MQTT.
"""

import json
from typing import Any

from app.core.tiempo import now_utc
from app.datos.canales.lora_virtual import LoraCanal
from app.datos.canales.mqtt_nodos import MQTT_OK, EnlaceMqttNodo
from app.datos.canales.rest_client import RestClient
from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.outbox_repo import OutboxRepo
from app.negocio.resumen_lora import construir_resumen_lora


class Entregador:
    def __init__(
        self,
        *,
        outbox: OutboxRepo,
        bitacora: BitacoraRepo,
        rest: RestClient,
        enlaces: dict[str, EnlaceMqttNodo],
        tokens: dict[str, str],
        lora: LoraCanal,
    ) -> None:
        self._outbox = outbox
        self._bitacora = bitacora
        self._rest = rest
        self._enlaces = enlaces
        self._tokens = tokens
        self._lora = lora

    def enviar_rest(self, uid: str, agregado: dict[str, Any]) -> bool:
        if not self._rest.configurado:
            return False  # Sin API configurada no es un intento de entrega.
        nodo = agregado["bridges"][0]["node_code"]
        token = self._tokens.get(nodo)
        if token is None:
            self._outbox.mark_attempt(uid, f"sin token para {nodo}")
            return False
        saliente = {
            **agregado,
            "delivery_status": "realtime",
            "transport": "rest",
            "sent_at": now_utc(),
        }
        ok, detalle = self._rest.enviar(saliente, token)
        if ok:
            self._outbox.mark_sent(uid, "sent_rest", detalle)
        else:
            self._outbox.mark_attempt(uid, detalle)
        return ok

    def enviar_mqtt_pendientes(self) -> set[str]:
        """Publica pendientes por el canal de su nodo. Devuelve los uids entregados."""
        entregados: set[str] = set()
        for uid, codificado, intentos in self._outbox.pending():
            payload = json.loads(codificado)
            if not payload.get("bridges"):
                self._outbox.mark_attempt(uid, "agregado sin bridges")
                continue
            nodo = payload["bridges"][0]["node_code"]
            enlace = self._enlaces.get(nodo)
            if enlace is None or not enlace.conectado():
                continue
            payload["delivery_status"] = "catch_up" if intentos else "realtime"
            payload["transport"] = "mqtt"
            payload["sent_at"] = now_utc()
            rc = enlace.publicar(payload)
            if rc == MQTT_OK:
                self._outbox.mark_sent(uid, "sent_mqtt", "mqtt:accepted")
                entregados.add(uid)
            else:
                self._outbox.mark_attempt(uid, str(rc))
        return entregados

    def enviar_lora(self, agregado: dict[str, Any]) -> bool:
        resultado = self._lora.transmitir_resumen(construir_resumen_lora(agregado))
        self._bitacora.log("INFO", f"LoRa {resultado.reason} latency_ms={resultado.latency_ms}")
        return resultado.success

    def nodos_configurados(self) -> list[str]:
        return sorted(self._tokens)

    def estado_mqtt(self) -> dict[str, bool]:
        return {nodo: enlace.conectado() for nodo, enlace in self._enlaces.items()}
