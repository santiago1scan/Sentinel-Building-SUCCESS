"""Abre y cierra incidentes (emergencias en curso) a medida que llegan los bloques."""

from typing import Any

from app.datos.repositorios.bitacora_repo import BitacoraRepo
from app.datos.repositorios.incidente_repo import IncidenteRepo
from app.datos.repositorios.outbox_repo import OutboxRepo


class GestorIncidentes:
    def __init__(self, *, outbox: OutboxRepo, incidentes: IncidenteRepo, bitacora: BitacoraRepo,
                 bloques_contexto: int, bloques_cierre: int) -> None:
        self._outbox = outbox
        self._incidentes = incidentes
        self._bitacora = bitacora
        self._contexto = bloques_contexto
        self._cierre = bloques_cierre

    def registrar(self, agregado: dict[str, Any]) -> None:
        """Llamar tras guardar el agregado en el outbox, uno por bloque."""
        if not agregado.get("bridges"):
            return
        nodo = agregado["bridges"][0]["node_code"]
        abierto = self._incidentes.abierto(nodo)
        if agregado["priority"] != "normal":
            if abierto:
                self._incidentes.emergencia_continua(abierto["id"])
                return
            rowid = self._outbox.rowid_de(agregado["message_uid"])
            if rowid is None:
                return
            previos = self._outbox.previos_normales(nodo, rowid, self._contexto)
            self._incidentes.abrir(nodo, agregado["generated_at"], rowid,
                                   previos[0] if previos else rowid)
            self._bitacora.log(
                "WARN", f"Incidente abierto en {nodo} desde {agregado['generated_at']} "
                        f"({len(previos)} bloques de contexto)")
        elif abierto and self._incidentes.bloque_normal(abierto["id"], self._cierre):
            self._bitacora.log("INFO", f"Incidente cerrado en {nodo}: vuelve a normal")
