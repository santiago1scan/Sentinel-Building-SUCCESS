"""Ensambla las capas: cliente del bridge y controlador de la simulación."""

from dataclasses import dataclass

from app.core.config import Settings
from app.datos.cliente_beta import ClienteBeta
from app.datos.cliente_bridge import ClienteBridge
from app.negocio.reflejo_beta import ReflejoBeta
from app.negocio.simulacion import ControladorSimulacion


@dataclass
class Contenedor:
    controlador: ControladorSimulacion


def crear_contenedor(ajustes: Settings) -> Contenedor:
    cliente = ClienteBridge(ajustes.bridge_url, ajustes.bridge_timeout)
    reflejo = ReflejoBeta(ClienteBeta(ajustes.beta_url, ajustes.beta_timeout))
    controlador = ControladorSimulacion(
        nodos=ajustes.nodos,
        intervalo_s=ajustes.interval,
        cliente=cliente,
        semilla=ajustes.seed,
        reflejo=reflejo,
    )
    # El resultado de cada comando reflejado se ve en el log del panel.
    reflejo.registrar = controlador.registrar_mensaje
    return Contenedor(controlador=controlador)
