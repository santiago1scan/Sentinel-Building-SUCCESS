"""Ensambla las capas: cliente del bridge y controlador de la simulación."""

from dataclasses import dataclass

from app.core.config import Settings
from app.datos.cliente_bridge import ClienteBridge
from app.negocio.simulacion import ControladorSimulacion


@dataclass
class Contenedor:
    controlador: ControladorSimulacion


def crear_contenedor(ajustes: Settings) -> Contenedor:
    cliente = ClienteBridge(ajustes.bridge_url, ajustes.bridge_timeout)
    controlador = ControladorSimulacion(
        nodos=ajustes.nodos,
        intervalo_s=ajustes.interval,
        cliente=cliente,
        semilla=ajustes.seed,
    )
    return Contenedor(controlador=controlador)
