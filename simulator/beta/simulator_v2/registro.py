"""Registro de nodos contra monolito-consulta (mismo flujo que el bridge principal).

1. Se solicita el registro con POST /registrations (código, nombre, edificio y zona).
2. Un administrador lo aprueba en consulta.
3. Se recoge el token con GET /registrations/{id} y X-Poll-Secret (se entrega una sola vez)
   y se guarda en NodeRegistryStore, de donde lo toma el envío REST.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import SENSORS, sensor_id
from .credentials import NodeRegistryStore

# sensor_type_id de la tabla sensor_type del backend, por modelo (ids sembrados en la BD actual:
# 1 ADXL355, 2 AMG8833, 3 BME688, 4 INA219). Si el catálogo cambia, se ajusta aquí.
SENSOR_TYPE_IDS = {"ADXL355": 1, "AMG8833": 2, "BME688": 3, "INA219": 4}


def node_sensors(node_code: str) -> list[dict[str, Any]]:
    """Los sensores del nodo con el código que Beta envía en cada resumen (p. ej. ADXL355-NODE-FLOOR-1)."""
    return [
        {"code": sensor_id(node_code, kind), "sensor_type_id": SENSOR_TYPE_IDS[profile.model]}
        for kind, profile in SENSORS.items()
    ]

_PUBLIC_FIELDS = ("registration_id", "name", "building_id", "zone_id", "status", "detail",
                  "requested_at", "expires_at", "updated_at")


class ConsultaError(Exception):
    """Falla al hablar con consulta. `status` es el código HTTP, o None si no hubo respuesta."""

    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class RegistroError(Exception):
    """Error de negocio con el código HTTP que debe ver quien llama."""

    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


def _message(body: Any) -> str:
    if isinstance(body, dict):
        for key in ("message", "detail"):
            if isinstance(body.get(key), str):
                return body[key]
    return ""


def _read_error(exc: urllib.error.HTTPError) -> tuple[int, Any]:
    try:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    except (OSError, ValueError):
        return exc.code, {}


class ConsultaClient:
    def __init__(self, base_url: str, timeout: float = 8.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def request_registration(self, code: str, name: str, building_id: int,
                             zone_id: int, sensors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + "/registrations",
            data=json.dumps({"code": code, "name": name, "building_id": building_id,
                             "zone_id": zone_id, "sensors": sensors or []}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status, body = _read_error(exc)
            raise ConsultaError(status, _message(body) or f"Consulta respondió {status}") from exc
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ConsultaError(None, str(exc)) from exc

    def collect(self, registration_id: str, poll_secret: str) -> tuple[int, dict[str, Any]]:
        """(estado HTTP, cuerpo): 202 pendiente, 200 aprobado con token, 404 no existe, 410 cerrada."""
        request = urllib.request.Request(
            f"{self.base_url}/registrations/{urllib.parse.quote(registration_id, safe='')}",
            headers={"X-Poll-Secret": poll_secret},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return _read_error(exc)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ConsultaError(None, str(exc)) from exc


class RegistrationService:
    def __init__(self, store: NodeRegistryStore, consulta: ConsultaClient,
                 nodes: tuple[str, ...]) -> None:
        self.store = store
        self.consulta = consulta
        self.nodes = nodes
        # Dos pestañas consultando a la vez: solo una recoge el token (se entrega una sola vez).
        self._lock = threading.Lock()

    def _check_node(self, node_code: str) -> None:
        if node_code not in self.nodes:
            raise RegistroError(404, f"Nodo desconocido: {node_code}")

    def status(self, node_code: str) -> dict[str, Any]:
        self._check_node(node_code)
        row = self.store.get_request(node_code)
        return {
            "nodo": node_code,
            "nodos": list(self.nodes),
            "consulta_configurada": self.consulta.configured,
            "registrado": self.store.has_credential(node_code),
            "credencial_activa": self.store.has_credential(node_code),
            "sensores": [sensor["code"] for sensor in node_sensors(node_code)],
            "registro": None if row is None else {f: row.get(f) for f in _PUBLIC_FIELDS},
        }

    def request(self, node_code: str, name: str, building_id: int, zone_id: int) -> dict[str, Any]:
        self._check_node(node_code)
        if not self.consulta.configured:
            raise RegistroError(503, "Beta no tiene configurada la URL de consulta "
                                     "(SENTINEL_CONSULTA_URL).")
        with self._lock:
            if self.store.has_credential(node_code):
                raise RegistroError(409, "Este nodo ya está registrado.")
            current = self.store.get_request(node_code)
            if current is not None and current["status"] == "pending":
                raise RegistroError(409, "Ya hay una solicitud pendiente de aprobación.")
            try:
                response = self.consulta.request_registration(
                    node_code, name, building_id, zone_id, node_sensors(node_code))
                registration_id = response["registration_id"]
                poll_secret = response["poll_secret"]
            except ConsultaError as exc:
                # 404 (edificio o zona), 409 (nodo o solicitud existente) y 422 se muestran tal cual.
                status = exc.status if exc.status in (404, 409, 422) else 502
                detail = exc.message if status != 502 else f"No se pudo contactar a consulta: {exc.message}"
                raise RegistroError(status, detail) from exc
            except KeyError as exc:
                raise RegistroError(502, "Consulta respondió sin los datos esperados.") from exc
            self.store.save_request(
                node_code, registration_id=registration_id, poll_secret=poll_secret, name=name,
                building_id=building_id, zone_id=zone_id, expires_at=response.get("expires_at"))
        return self.status(node_code)

    def poll(self, node_code: str) -> dict[str, Any]:
        """Si hay una solicitud pendiente, pregunta a consulta y guarda el token cuando llega."""
        self._check_node(node_code)
        with self._lock:
            row = self.store.get_request(node_code)
            if row is None or row["status"] != "pending":
                return self.status(node_code)
            try:
                http_status, body = self.consulta.collect(row["registration_id"], row["poll_secret"])
            except ConsultaError as exc:
                self.store.update_request(node_code, "pending",
                                          f"No se pudo contactar a consulta: {exc.message}")
                return self.status(node_code)
            self._apply(node_code, http_status, body)
        return self.status(node_code)

    def _apply(self, node_code: str, http_status: int, body: dict[str, Any]) -> None:
        store = self.store
        if http_status == 202:
            store.update_request(node_code, "pending", "Esperando aprobación del administrador")
        elif http_status == 200:
            token = body.get("token")
            if not isinstance(token, str) or not token:
                store.update_request(node_code, "pending", "Consulta aprobó sin entregar el token")
                return
            store.save_credential(node_code, body.get("node_id"), token)
            store.update_request(node_code, "delivered",
                                 "Credencial recibida y aplicada: el envío REST ya la usa.",
                                 clear_secret=True)
        elif http_status == 404:
            store.update_request(
                node_code, "expired",
                "La solicitud ya no existe en consulta (venció o consulta se reinició). "
                "Envía una nueva.", clear_secret=True)
        elif http_status == 410:
            store.update_request(
                node_code, "gone",
                _message(body) or "La solicitud fue rechazada o el token ya se entregó.",
                clear_secret=True)
        else:
            store.update_request(node_code, "pending",
                                 f"Consulta respondió {http_status}: {_message(body)}".rstrip(": "))
