"""Hilo en segundo plano que llama a ServicioIngesta.drenar() cada cierto tiempo."""

import threading

from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.negocio.ingesta import ServicioIngesta


class Drenador:
    def __init__(self, ingesta: ServicioIngesta, bitacora: BitacoraRepo, intervalo_s: float) -> None:
        self._ingesta = ingesta
        self._bitacora = bitacora
        self._intervalo = intervalo_s
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._bucle, name="drenaje-outbox", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self) -> None:
        self._parar.set()
        self._hilo.join(timeout=self._intervalo + 10)

    def _bucle(self) -> None:
        # wait() devuelve True al detenerse: el bucle termina sin esperar el intervalo completo.
        while not self._parar.wait(self._intervalo):
            try:
                self._ingesta.drenar()
            except Exception as exc:  # un fallo no debe matar el hilo
                try:
                    self._bitacora.log("ERROR", f"Drenaje falló: {exc}")
                except Exception:
                    pass
