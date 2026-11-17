"""Configuración del simulador desde variables de entorno (prefijo SENTINEL_).

Solo usa la biblioteca estándar, para correr con el Docker y las dependencias que
ya existen para el simulador. La única conexión de salida es el bridge: no hay
variables del backend, del broker MQTT ni de LoRa.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


def _texto_a_bool(valor: str | None) -> bool:
    return (valor or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    bridge_url: str = "http://bridge:8766"
    bridge_timeout: float = 10.0
    interval: float = 30.0
    # Códigos de nodo que se simulan, separados por coma. Zonas y edificios los conoce el bridge.
    sim_nodes: str = "NODE-FLOOR-1,NODE-FLOOR-2"
    # Si es true, el ciclo de lecturas arranca solo al iniciar el servicio.
    autostart: bool = False
    # Semilla opcional para repetir una simulación.
    seed: int | None = None

    def __post_init__(self) -> None:
        if not self.bridge_url.startswith(("http://", "https://")):
            raise ValueError("SENTINEL_BRIDGE_URL debe ser una URL HTTP o HTTPS")
        if self.bridge_timeout <= 0:
            raise ValueError("SENTINEL_BRIDGE_TIMEOUT debe ser positivo")
        if self.interval <= 0:
            raise ValueError("SENTINEL_INTERVAL debe ser positivo")
        if not self.nodos:
            raise ValueError("SENTINEL_SIM_NODES debe tener al menos un nodo")

    @property
    def nodos(self) -> list[str]:
        nodos = [item.strip() for item in self.sim_nodes.split(",") if item.strip()]
        return list(dict.fromkeys(nodos))

    @classmethod
    def desde_entorno(cls) -> "Settings":
        semilla = os.getenv("SENTINEL_SEED")
        return cls(
            bridge_url=os.getenv("SENTINEL_BRIDGE_URL", cls.bridge_url),
            bridge_timeout=float(os.getenv("SENTINEL_BRIDGE_TIMEOUT", cls.bridge_timeout)),
            interval=float(os.getenv("SENTINEL_INTERVAL", cls.interval)),
            sim_nodes=os.getenv("SENTINEL_SIM_NODES", cls.sim_nodes),
            autostart=_texto_a_bool(os.getenv("SENTINEL_AUTOSTART")),
            seed=int(semilla) if semilla else None,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.desde_entorno()
