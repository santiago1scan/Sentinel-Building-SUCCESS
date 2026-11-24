"""Arma el evento que el bridge recibe en POST /v1/readings.

El evento no lleva edificio, zona, piso ni coordenadas: eso lo resuelve el bridge
con su propio catálogo a partir del código del nodo.
"""

import random
import uuid
from typing import Any

from app.core.tiempo import now_utc
from app.negocio.generacion.lecturas import GENERADORES
from app.negocio.sensores import PRIORIDAD_ANOMALIA, SENSORES, TIPOS_SENSOR, sensor_id


def crear_evento(nodo: str, tipo: str, secuencia: int, payload: dict[str, Any],
                 prioridad: str = "normal", calidad: str = "valid") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "sensor_reading",
        "node_id": nodo,
        "sensor_id": sensor_id(nodo, tipo),
        "sensor_type": tipo,
        "sensor_model": SENSORES[tipo]["model"],
        "generated_at": now_utc(),
        "sequence_number": secuencia,
        "priority": prioridad,
        "quality": calidad,
        # Las lecturas normales esperan el intervalo; una anomalía se envía de inmediato.
        "delivery_policy": "immediate" if prioridad in {"high", "critical"} else "periodic",
        "transport": "http",
        "payload": payload,
    }


def eventos_nodo(nodo: str, secuencia: int, anomalias: dict[str, str],
                 silenciados: set[tuple[str, str]], rng: random.Random) -> list[dict[str, Any]]:
    """Una lectura por sensor del nodo; los sensores sin respuesta no emiten.

    `anomalias`: tipo de sensor → modo ("fire", "candle", "spray", "faulty"). Toda anomalía sale de inmediato; la
    gravedad no la pone el simulador, la deduce el backend.
    """
    eventos = []
    for tipo in TIPOS_SENSOR:
        if (nodo, tipo) in silenciados:
            continue
        modo = anomalias.get(tipo)
        anomalia = modo is not None
        payload = GENERADORES[tipo](rng, modo)
        eventos.append(crear_evento(
            nodo, tipo, secuencia, payload,
            PRIORIDAD_ANOMALIA[tipo] if anomalia else "normal",
            "simulated_anomaly" if anomalia else "valid",
        ))
    return eventos
