"""Único canal de salida del simulador: el bridge, por HTTP.

No hay outbox ni reintentos persistentes: si el bridge no responde, el ciclo lo
registra y la lectura de ese ciclo se descarta.
"""

import json
import urllib.error
import urllib.request
from typing import Any


class ClienteBridgeError(Exception):
    """El bridge no respondió o rechazó la petición."""


class ClienteBridge:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def enviar_lecturas(self, lecturas: list[dict[str, Any]]) -> dict[str, Any]:
        """POST /v1/readings con la lista de lecturas. Devuelve la respuesta del bridge."""
        peticion = urllib.request.Request(
            self.base_url + "/v1/readings",
            data=json.dumps({"readings": lecturas}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ClienteBridgeError(str(exc)) from exc

    def estado(self, timeout: float = 2.0) -> dict[str, Any] | None:
        """GET /health del bridge. None si no responde."""
        try:
            with urllib.request.urlopen(self.base_url + "/health", timeout=timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
            return None
