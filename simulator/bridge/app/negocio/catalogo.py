"""Catálogo de nodos del edificio. Por defecto replica el catálogo fijo del bridge
actual; puede sobrescribirse con SENTINEL_CATALOGO_JSON."""

import copy
import json
from typing import Any

CATALOGO_POR_DEFECTO: dict[str, dict[str, Any]] = {
    "NODE-FLOOR-1": {"zone_id": "ZONE-F1", "floor": 1, "bridge_name": "Bridge 1 - Piso 1"},
    "NODE-FLOOR-2": {"zone_id": "ZONE-F2", "floor": 2, "bridge_name": "Bridge 2 - Piso 2"},
}

_CAMPOS_REQUERIDOS = ("zone_id", "floor", "bridge_name")


def cargar_catalogo(texto: str | None) -> dict[str, dict[str, Any]]:
    if not texto:
        return copy.deepcopy(CATALOGO_POR_DEFECTO)
    datos = json.loads(texto)
    if not isinstance(datos, dict) or not datos:
        raise ValueError("El catálogo debe ser un objeto JSON con al menos un nodo")
    for nodo, info in datos.items():
        faltantes = [campo for campo in _CAMPOS_REQUERIDOS if campo not in info]
        if faltantes:
            raise ValueError(f"Nodo {nodo} sin campos: {', '.join(faltantes)}")
    return datos
