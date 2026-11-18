"""¿Está el bridge conectado a la red y por qué canal está entregando?

Canales: REST (se sondea el /health del backend), MQTT (un enlace por nodo) y LoRa (respaldo
virtual: no se sondea; solo se sabe si entregó).

Estado de la red, según REST y MQTT (LoRa no cuenta):
  en_linea      responden todos
  parcial       responde alguno
  sin_conexion  no responde ninguno (o no hay canales configurados)

Canal en uso: el de la última entrega confirmada, si fue hace menos de `ventana_s`. REST lleva los
datos normales y MQTT las emergencias, así que MQTT solo aparece en uso durante un incidente.
El sondeo a REST se guarda unos segundos: la página pregunta cada 10 s y no debe martillar al backend.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.datos.canales.rest_client import RestClient

NOMBRES = {"rest": "REST", "mqtt": "MQTT", "lora": "LoRa"}


def _edad_s(hora: str | None, ahora: datetime) -> float | None:
    if not hora:
        return None
    try:
        return (ahora - datetime.fromisoformat(hora)).total_seconds()
    except ValueError:
        return None


class ServicioConectividad:
    def __init__(self, *, rest: RestClient, estado_mqtt: Callable[[], dict[str, bool]],
                 ultimas_entregas: Callable[[], dict[str, str | None]] = lambda: {},
                 vigencia_s: float = 8.0, ventana_s: float = 90.0,
                 reloj: Callable[[], float] = time.monotonic,
                 ahora: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._rest = rest
        self._estado_mqtt = estado_mqtt
        self._ultimas = ultimas_entregas
        self._vigencia = vigencia_s
        self._ventana = ventana_s
        self._reloj = reloj
        self._ahora = ahora
        self._candado = threading.Lock()
        self._ultimo: tuple[float, bool, str] | None = None

    def _backend(self) -> dict[str, Any]:
        if not self._rest.configurado:
            return {"configurado": False, "alcanzable": False, "detalle": "Sin URL del backend (SENTINEL_API_URL)"}
        with self._candado:
            ahora = self._reloj()
            if self._ultimo is None or ahora - self._ultimo[0] >= self._vigencia:
                ok, detalle = self._rest.sondear()
                self._ultimo = (ahora, ok, detalle)
            _, ok, detalle = self._ultimo
        return {"configurado": True, "alcanzable": ok, "detalle": detalle}

    def estado(self) -> dict[str, Any]:
        backend = self._backend()
        mqtt = self._estado_mqtt()
        canales_red = ([backend["alcanzable"]] if backend["configurado"] else []) + list(mqtt.values())
        activos = sum(1 for ok in canales_red if ok)
        if not canales_red or activos == 0:
            nivel = "sin_conexion"
        elif activos == len(canales_red):
            nivel = "en_linea"
        else:
            nivel = "parcial"

        ultimas = self._ultimas()
        ahora = self._ahora()
        edades = {canal: _edad_s(ultimas.get(canal), ahora) for canal in NOMBRES}
        recientes = {c: e for c, e in edades.items() if e is not None and e <= self._ventana}
        en_uso = min(recientes, key=recientes.get) if recientes else None

        canales = {
            "rest": {"conectado": backend["alcanzable"] if backend["configurado"] else None},
            "mqtt": {"conectado": (all(mqtt.values()) if mqtt else None)},
            "lora": {"conectado": None},  # respaldo virtual: sin enlace que medir
        }
        for nombre, info in canales.items():
            info["ultima_entrega"] = ultimas.get(nombre)
            info["en_uso"] = nombre == en_uso
        return {"estado": nivel, "en_uso": en_uso, "canales": canales,
                "canales_activos": activos, "canales_total": len(canales_red),
                "backend": backend, "mqtt": mqtt}
