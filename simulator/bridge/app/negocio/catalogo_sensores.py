"""Catálogo de tipos de sensor: el bridge solo lo consume de consulta, no lo guarda.

Cada tipo trae `metrics` (código, nombre, unidad, rango normal y si alarma por abajo o por
arriba). Aquí se traducen las fallas de consulta a errores de negocio con el código HTTP
que debe ver quien llama.
"""

from typing import Any

from app.datos.canales.consulta_client import ConsultaClient, ConsultaError


class CatalogoError(Exception):
    """Error de negocio con el código HTTP que debe ver quien llama."""

    def __init__(self, estado_http: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.mensaje = mensaje


class ServicioCatalogoSensores:
    def __init__(self, consulta: ConsultaClient) -> None:
        self._consulta = consulta

    def listar(self, token: str) -> list[dict[str, Any]]:
        self._exigir_configurado()
        try:
            return self._consulta.listar_tipos_sensor(token)
        except ConsultaError as exc:
            raise self._traducir(exc) from exc

    def obtener(self, sensor_type_id: int, token: str) -> dict[str, Any]:
        self._exigir_configurado()
        try:
            return self._consulta.obtener_tipo_sensor(sensor_type_id, token)
        except ConsultaError as exc:
            raise self._traducir(exc) from exc

    def _exigir_configurado(self) -> None:
        if not self._consulta.configurado:
            raise CatalogoError(503, "El bridge no tiene configurada la URL de consulta "
                                     "(SENTINEL_CONSULTA_URL).")

    @staticmethod
    def _traducir(exc: ConsultaError) -> CatalogoError:
        if exc.estado == 404:
            return CatalogoError(404, exc.mensaje or "SensorType not found")
        if exc.estado in (401, 403):
            return CatalogoError(exc.estado, exc.mensaje)
        return CatalogoError(502, f"No se pudo consultar el catálogo: {exc.mensaje}")
