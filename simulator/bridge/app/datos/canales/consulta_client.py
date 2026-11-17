"""Cliente HTTP de monolito-consulta para registrar el nodo.

POST /registrations no requiere autenticación (lo hace el bridge); el administrador aprueba
en consulta con Firebase, y el bridge recoge el token con GET /registrations/{id} y su
X-Poll-Secret. Solo transporte: las decisiones están en negocio/registro_nodo.py.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ConsultaError(Exception):
    """Falla al hablar con consulta. `estado` es el código HTTP, o None si no hubo respuesta."""

    def __init__(self, estado: int | None, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def _mensaje(cuerpo: Any) -> str:
    if isinstance(cuerpo, dict):
        for clave in ("message", "detail"):
            if isinstance(cuerpo.get(clave), str):
                return cuerpo[clave]
    return ""


def _leer_error(exc: urllib.error.HTTPError) -> tuple[int, Any]:
    try:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    except (OSError, ValueError):
        return exc.code, {}


class ConsultaClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def configurado(self) -> bool:
        return bool(self.base_url)

    def solicitar_registro(self, codigo: str, nombre: str, building_id: int,
                           zone_id: int) -> dict[str, Any]:
        peticion = urllib.request.Request(
            self.base_url + "/registrations",
            data=json.dumps({"code": codigo, "name": nombre,
                             "building_id": building_id, "zone_id": zone_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            estado, cuerpo = _leer_error(exc)
            raise ConsultaError(estado, _mensaje(cuerpo) or f"Consulta respondió {estado}") from exc
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ConsultaError(None, str(exc)) from exc

    def recoger(self, registration_id: str, poll_secret: str) -> tuple[int, dict[str, Any]]:
        """Devuelve (estado HTTP, cuerpo) para cualquier respuesta de consulta.

        202 = pendiente, 200 = aprobado con el token (se entrega una sola vez),
        404 = no existe o el secreto no coincide, 410 = rechazada o ya entregada.
        Solo lanza ConsultaError si no hubo respuesta.
        """
        peticion = urllib.request.Request(
            f"{self.base_url}/registrations/{urllib.parse.quote(registration_id, safe='')}",
            headers={"X-Poll-Secret": poll_secret},
            method="GET",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return _leer_error(exc)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ConsultaError(None, str(exc)) from exc
