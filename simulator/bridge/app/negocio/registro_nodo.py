"""Registro del nodo contra el backend: solicitud, espera de aprobación y recogida del token.

Flujo de nacimiento del nodo:
1. El bridge solicita el registro a consulta (código, nombre, edificio y zona).
2. Un administrador lo aprueba en consulta.
3. El bridge recoge el token (se entrega una sola vez), lo guarda y lo aplica: REST y MQTT
   pasan a usarlo sin reiniciar.

El poll_secret y el token nunca salen del bridge: la API solo devuelve el estado.
"""

import threading
from typing import Any, Callable

from app.datos.canales.consulta_client import ConsultaClient, ConsultaError
from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.registro_repo import RegistroRepo

_CAMPOS_PUBLICOS = ("registration_id", "name", "building_id", "zone_id", "status", "detail",
                    "requested_at", "expires_at", "updated_at")


class RegistroError(Exception):
    """Error de negocio con el código HTTP que debe ver quien llama."""

    def __init__(self, estado_http: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.mensaje = mensaje


def _mensaje(cuerpo: dict[str, Any]) -> str:
    for clave in ("message", "detail"):
        if isinstance(cuerpo.get(clave), str):
            return cuerpo[clave]
    return ""


class ServicioRegistro:
    def __init__(
        self,
        *,
        repo: RegistroRepo,
        consulta: ConsultaClient,
        bitacora: BitacoraRepo,
        codigo_nodo: str,
        aplicar_credencial: Callable[[str, str], None],
        tiene_token: Callable[[str], bool],
    ) -> None:
        self._repo = repo
        self._consulta = consulta
        self._bitacora = bitacora
        self._codigo = codigo_nodo
        self._aplicar = aplicar_credencial
        self._tiene_token = tiene_token
        # Dos pestañas consultando a la vez: solo una recoge el token (se entrega una sola vez).
        self._candado = threading.Lock()

    def estado(self) -> dict[str, Any]:
        fila = self._repo.obtener(self._codigo)
        return {
            "nodo": self._codigo,
            "consulta_configurada": self._consulta.configurado,
            "registrado": self._repo.tiene_credencial(self._codigo),
            "credencial_activa": self._tiene_token(self._codigo),
            "registro": None if fila is None else {campo: fila[campo] for campo in _CAMPOS_PUBLICOS},
        }

    def solicitar(self, nombre: str, building_id: int, zone_id: int) -> dict[str, Any]:
        if not self._consulta.configurado:
            raise RegistroError(503, "El bridge no tiene configurada la URL de consulta "
                                     "(SENTINEL_CONSULTA_URL).")
        with self._candado:
            if self._repo.tiene_credencial(self._codigo):
                raise RegistroError(409, "Este nodo ya está registrado.")
            actual = self._repo.obtener(self._codigo)
            if actual is not None and actual["status"] == "pending":
                raise RegistroError(409, "Ya hay una solicitud pendiente de aprobación.")
            try:
                respuesta = self._consulta.solicitar_registro(
                    self._codigo, nombre, building_id, zone_id)
                registration_id = respuesta["registration_id"]
                poll_secret = respuesta["poll_secret"]
            except ConsultaError as exc:
                # 404 (edificio o zona), 409 (nodo o solicitud existente) y 422 se muestran tal cual.
                estado = exc.estado if exc.estado in (404, 409, 422) else 502
                detalle = exc.mensaje if estado != 502 else f"No se pudo contactar a consulta: {exc.mensaje}"
                raise RegistroError(estado, detalle) from exc
            except KeyError as exc:
                raise RegistroError(502, "Consulta respondió sin los datos esperados.") from exc

            self._repo.guardar_solicitud(
                codigo=self._codigo, registration_id=registration_id, poll_secret=poll_secret,
                nombre=nombre, building_id=building_id, zone_id=zone_id,
                expires_at=respuesta.get("expires_at"))
            self._bitacora.log("INFO", f"Registro solicitado para {self._codigo} "
                                       f"(solicitud {registration_id})")
        return self.estado()

    def consultar(self) -> dict[str, Any]:
        """Si hay una solicitud pendiente, pregunta a consulta y aplica el token cuando llega."""
        with self._candado:
            fila = self._repo.obtener(self._codigo)
            if fila is None or fila["status"] != "pending":
                return self.estado()
            try:
                estado_http, cuerpo = self._consulta.recoger(
                    fila["registration_id"], fila["poll_secret"])
            except ConsultaError as exc:
                self._repo.actualizar(self._codigo, "pending",
                                      f"No se pudo contactar a consulta: {exc.mensaje}")
                return self.estado()
            self._aplicar_respuesta(estado_http, cuerpo)
        return self.estado()

    def _aplicar_respuesta(self, estado_http: int, cuerpo: dict[str, Any]) -> None:
        codigo = self._codigo
        if estado_http == 202:
            self._repo.actualizar(codigo, "pending", "Esperando aprobación del administrador")
        elif estado_http == 200:
            token = cuerpo.get("token")
            if not isinstance(token, str) or not token:
                self._repo.actualizar(codigo, "pending", "Consulta aprobó sin entregar el token")
                return
            self._repo.guardar_credencial(codigo, cuerpo.get("node_id"), token)
            self._aplicar(codigo, token)
            self._repo.actualizar(codigo, "delivered",
                                  "Credencial recibida y aplicada: REST y MQTT ya la usan.",
                                  limpiar_secreto=True)
            self._bitacora.log("INFO", f"Nodo {codigo} registrado; credencial guardada")
        elif estado_http == 404:
            self._repo.actualizar(
                codigo, "expired",
                "La solicitud ya no existe en consulta (venció o consulta se reinició). "
                "Envía una nueva.", limpiar_secreto=True)
        elif estado_http == 410:
            self._repo.actualizar(
                codigo, "gone",
                _mensaje(cuerpo) or "La solicitud fue rechazada o el token ya se entregó.",
                limpiar_secreto=True)
        else:
            self._repo.actualizar(codigo, "pending",
                                  f"Consulta respondió {estado_http}: {_mensaje(cuerpo)}".rstrip(": "))
