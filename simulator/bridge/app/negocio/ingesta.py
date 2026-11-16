"""Caso de uso principal: recibir lecturas, guardarlas, agregarlas y entregarlas.

Mismo orden que bridge_service.py: las lecturas se guardan antes de agregarlas.
"""

import json
import threading
from typing import Any

from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.lecturas_repo import LecturasRepo
from app.datos.repositorios.outbox_repo import OutboxRepo
from app.negocio.agregacion import construir_agregados
from app.negocio.entrega import Entregador


class ServicioIngesta:
    def __init__(
        self,
        *,
        lecturas: LecturasRepo,
        outbox: OutboxRepo,
        bitacora: BitacoraRepo,
        entregador: Entregador,
        catalogo: dict[str, dict[str, Any]],
        codigo_edificio: str,
        intervalo_s: float,
    ) -> None:
        self._lecturas = lecturas
        self._outbox = outbox
        self._bitacora = bitacora
        self._entregador = entregador
        self._catalogo = catalogo
        self._codigo = codigo_edificio
        self._intervalo = intervalo_s
        self._secuencia = 0
        # Serializa las ingestas: evita carreras sobre la secuencia (el original no lo hacía).
        self._candado = threading.Lock()

    def ingerir(self, lecturas: list[dict[str, Any]]) -> dict[str, Any]:
        if not lecturas:
            raise ValueError("El bridge necesita al menos una lectura")

        with self._candado:
            insertadas = self._lecturas.save_readings(lecturas)
            self._secuencia += 1
            agregados = construir_agregados(
                lecturas, self._codigo, self._intervalo, self._secuencia, self._catalogo)

            en_tiempo_real: set[str] = set()
            for agregado in agregados:
                self._outbox.save_aggregate(agregado)
                if self._entregador.enviar_rest(agregado["message_uid"], agregado):
                    en_tiempo_real.add(agregado["message_uid"])

            por_mqtt = self._entregador.enviar_mqtt_pendientes()
            entregados = en_tiempo_real | por_mqtt

            lora_enviados = 0
            for agregado in agregados:
                if agregado["message_uid"] not in entregados and \
                        self._entregador.enviar_lora(agregado):
                    lora_enviados += 1

            resultado = {
                "accepted": True,
                "raw_inserted": insertadas,
                "nodes": len(agregados),
                "rest_realtime": len(en_tiempo_real),
                "mqtt_catch_up": len(por_mqtt),
                "lora_summary": lora_enviados,
                "storage": self.almacenamiento(),
            }
            self._bitacora.log("INFO", json.dumps(resultado, ensure_ascii=False))
            return resultado

    def almacenamiento(self) -> dict[str, int]:
        return {"raw_readings": self._lecturas.count(), **self._outbox.counts()}

    def salud(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "component": "bridge",
            "nodes": self._entregador.nodos_configurados(),
            "mqtt_connected": self._entregador.estado_mqtt(),
            "storage": self.almacenamiento(),
        }

    def registrar_error(self, detalle: str) -> None:
        self._bitacora.log("ERROR", detalle)
