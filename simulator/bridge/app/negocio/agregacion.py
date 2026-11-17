"""Un mensaje agregado por nodo: cada uno viaja con la identidad de su nodo."""

from collections import defaultdict
from typing import Any

from app.negocio.telemetria_standard import aggregate_readings


def construir_agregados(
    lecturas: list[dict[str, Any]],
    building_code: str,
    interval_s: float,
    sequence: int,
    catalogo: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    por_nodo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for lectura in lecturas:
        nodo = lectura["node_id"]
        if nodo not in catalogo:
            raise ValueError(f"Nodo desconocido en la lectura: {nodo}")
        por_nodo[nodo].append(lectura)
    return [
        aggregate_readings(items, building_code, interval_s, sequence, catalogo)
        for _, items in sorted(por_nodo.items())
    ]
