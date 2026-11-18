"""Refleja en Beta las anomalías de este simulador, en segundo plano y en orden.

El controlador decide con su candado; aquí solo se encolan los comandos. Un hilo los envía de uno en uno
(así el orden poner/quitar se conserva) y registra el resultado en el log del panel. Si Beta no está o
falla, la simulación de este panel sigue igual: el reflejo nunca la bloquea.
"""

import queue
import threading
from typing import Callable

from app.datos.cliente_beta import ClienteBeta, ClienteBetaError


class ReflejoBeta:
    def __init__(self, cliente: ClienteBeta, registrar: Callable[[str], None] | None = None) -> None:
        self.cliente = cliente
        self.registrar: Callable[[str], None] = registrar or (lambda texto: None)
        self._cola: queue.Queue[tuple[str, str, bool]] = queue.Queue()
        self._hilo: threading.Thread | None = None
        self._candado = threading.Lock()

    @property
    def activo(self) -> bool:
        return self.cliente.configurado

    def anomalia(self, nodo: str, tipo_sensor: str, activa: bool) -> None:
        if not self.activo:
            return
        self._asegurar_hilo()
        self._cola.put((nodo, tipo_sensor, activa))

    def esperar(self, timeout: float = 5.0) -> None:
        """Bloquea hasta que se hayan enviado los comandos pendientes (para pruebas y cierre)."""
        if self._hilo is None:
            return
        fin = threading.Event()
        threading.Thread(target=lambda: (self._cola.join(), fin.set()), daemon=True).start()
        fin.wait(timeout)

    def _asegurar_hilo(self) -> None:
        with self._candado:
            if self._hilo is None or not self._hilo.is_alive():
                self._hilo = threading.Thread(target=self._bucle, name="reflejo-beta", daemon=True)
                self._hilo.start()

    def _bucle(self) -> None:
        while True:
            nodo, tipo, activa = self._cola.get()
            accion = "anomaly" if activa else "clear"
            try:
                self.cliente.anomalia(nodo, tipo, activa)
                self.registrar(f"beta | {accion} {nodo} {tipo} | reflejado")
            except ClienteBetaError as exc:
                self.registrar(f"beta | {accion} {nodo} {tipo} | no se pudo reflejar: {exc}")
            finally:
                self._cola.task_done()
