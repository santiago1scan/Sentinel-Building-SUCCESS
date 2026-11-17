"""Compara el agregado del monolito con el módulo original del simulador.

Solo corre si se monta el directorio del simulador y se indica en SENTINEL_SIM_DIR:
    docker run --rm -v <ruta>/simulator:/sim:ro -e SENTINEL_SIM_DIR=/sim <imagen> pytest -q
"""

import importlib.util
import os
from pathlib import Path

import pytest

from app.negocio import telemetria_standard
from app.negocio.agregacion import construir_agregados
from app.negocio.catalogo import CATALOGO_POR_DEFECTO

SIM_DIR = os.getenv("SENTINEL_SIM_DIR")
pytestmark = pytest.mark.skipif(not SIM_DIR, reason="requiere SENTINEL_SIM_DIR")

# uuid4 y la hora de envío cambian en cada corrida; el resto debe ser idéntico.
CAMPOS_VARIABLES = {"message_uid", "generated_at"}


def cargar_original():
    spec = importlib.util.spec_from_file_location(
        "telemetry_standard_original", Path(SIM_DIR) / "telemetry_standard.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def lecturas_fijas():
    base = {
        "sensor_model": "MPU-6050", "priority": "normal",
        "generated_at": "2026-11-16T10:00:00.000+00:00",
    }
    return [
        {**base, "event_id": "e1", "node_id": "NODE-FLOOR-1", "sensor_id": "S1",
         "sensor_type": "accelerometer",
         "payload": {"x_g": 0.1, "y_g": 0.2, "z_g": 1.0, "rms_g": 1.0, "frequency_hz": 5.0}},
        {**base, "event_id": "e2", "node_id": "NODE-FLOOR-1", "sensor_id": "S2",
         "sensor_type": "power_monitor",
         "payload": {"bus_voltage_v": 12.0, "current_ma": 100.0, "power_mw": 1200.0,
                     "battery_low": False}},
        {**base, "event_id": "e3", "node_id": "NODE-FLOOR-2", "sensor_id": "S3",
         "sensor_type": "thermal_array", "priority": "high",
         "payload": {"average_c": 30.0, "maximum_c": 45.0, "hot_pixels": 2}},
    ]


def sin_variables(agregado):
    return {k: v for k, v in agregado.items() if k not in CAMPOS_VARIABLES}


def test_agregados_identicos_al_original():
    original = cargar_original()
    lecturas = lecturas_fijas()
    esperado = original.aggregate_readings(
        [l for l in lecturas if l["node_id"] == "NODE-FLOOR-1"],
        "SB-001", 30.0, 5, CATALOGO_POR_DEFECTO)
    obtenido = construir_agregados(
        [l for l in lecturas if l["node_id"] == "NODE-FLOOR-1"],
        "SB-001", 30.0, 5, CATALOGO_POR_DEFECTO)
    assert len(obtenido) == 1
    assert sin_variables(obtenido[0]) == sin_variables(esperado)


def test_constantes_coinciden_con_original():
    original = cargar_original()
    assert telemetria_standard.SCHEMA_VERSION == original.SCHEMA_VERSION
    assert telemetria_standard.MEASUREMENT_TYPES == original.MEASUREMENT_TYPES
