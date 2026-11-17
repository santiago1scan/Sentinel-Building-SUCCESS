"""Gráficas de las lecturas del nodo de este bridge.

Cada gráfica es una definición del registro `GRAFICAS`: agregar una nueva es agregar
una entrada (y un <div data-grafica="..."> en la página). Los resultados se guardan
en caché 30 s para que varias pestañas abiertas no multipliquen las consultas.
"""

import math
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.datos.repositorios.graficas_repo import GraficasRepo

CACHE_SEGUNDOS = 30
MINUTOS_MAXIMOS = 1440
MAX_PUNTOS = 400

GRAFICAS: dict[str, dict[str, Any]] = {
    "acelerometro-rms": {
        "titulo": "Acelerómetro · vibración RMS", "tipo": "linea",
        "sensor": "accelerometer", "campo": "rms_g", "unidad": "g"},
    "termico-maximo": {
        "titulo": "Térmico · temperatura máxima", "tipo": "linea",
        "sensor": "thermal_array", "campo": "maximum_c", "unidad": "°C"},
    "gas-iaq": {
        "titulo": "Gas · índice de calidad del aire", "tipo": "linea",
        "sensor": "gas_environmental", "campo": "iaq_index", "unidad": "IAQ"},
    "energia-voltaje": {
        "titulo": "Energía · voltaje del bus", "tipo": "linea",
        "sensor": "power_monitor", "campo": "bus_voltage_v", "unidad": "V"},
    "prioridad": {
        "titulo": "Prioridad de las lecturas por minuto", "tipo": "prioridad"},
}


def _reducir(puntos: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Promedia por tramos si hay demasiados puntos para dibujar."""
    if len(puntos) <= MAX_PUNTOS:
        return puntos
    paso = math.ceil(len(puntos) / MAX_PUNTOS)
    reducidos = []
    for i in range(0, len(puntos), paso):
        tramo = puntos[i:i + paso]
        reducidos.append((sum(t for t, _ in tramo) / len(tramo), sum(v for _, v in tramo) / len(tramo)))
    return reducidos


class ServicioGraficas:
    def __init__(self, repo: GraficasRepo, nodo: str) -> None:
        self._repo = repo
        self.nodo = nodo
        self._cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
        self._candado = threading.Lock()

    @staticmethod
    def nombres() -> list[str]:
        """Gráficas definidas, en orden; la página inicia una tarjeta por cada una."""
        return list(GRAFICAS)

    def datos(self, nombre: str, minutos: int) -> dict[str, Any]:
        if nombre not in GRAFICAS:
            raise ValueError(f"Gráfica desconocida: {nombre}")
        minutos = max(1, min(int(minutos), MINUTOS_MAXIMOS))
        clave = (nombre, minutos)
        with self._candado:
            guardado = self._cache.get(clave)
            if guardado and guardado[0] > time.monotonic():
                return guardado[1]
        resultado = self._calcular(nombre, minutos)
        with self._candado:
            self._cache[clave] = (time.monotonic() + CACHE_SEGUNDOS, resultado)
        return resultado

    def _calcular(self, nombre: str, minutos: int) -> dict[str, Any]:
        definicion = GRAFICAS[nombre]
        ahora = datetime.now(timezone.utc)
        desde = ahora - timedelta(minutes=minutos)
        desde_iso = desde.isoformat(timespec="milliseconds")
        base = {"titulo": definicion["titulo"], "tipo": definicion["tipo"], "minutos": minutos,
                "desde_ts": desde.timestamp(), "hasta_ts": ahora.timestamp(), "nodo": self.nodo}

        if definicion["tipo"] == "linea":
            filas = self._repo.serie(self.nodo, definicion["sensor"], definicion["campo"], desde_iso)
            puntos = [(datetime.fromisoformat(hora).timestamp(), valor) for hora, valor in filas]
            return {**base, "unidad": definicion["unidad"], "puntos": _reducir(puntos)}

        cubos: dict[str, dict[str, Any]] = {}
        for minuto, prioridad, cantidad in self._repo.prioridades_por_minuto(self.nodo, desde_iso):
            cubo = cubos.setdefault(minuto, {
                "ts": datetime.fromisoformat(minuto + ":00+00:00").timestamp(),
                "normal": 0, "high": 0, "critical": 0})
            # Igual que el bridge al agregar: lo que no es high ni critical cuenta como normal.
            cubo[prioridad if prioridad in ("high", "critical") else "normal"] += cantidad
        return {**base, "minutos_datos": list(cubos.values())}
