import json

import pytest

from app.negocio.agregacion import construir_agregados
from app.negocio.catalogo import CATALOGO_POR_DEFECTO, cargar_catalogo


def lectura(node="NODE-FLOOR-1", sensor_type="accelerometer", priority="normal", n=0):
    return {
        "event_id": f"evt-{node}-{sensor_type}-{n}",
        "node_id": node,
        "sensor_id": f"SENSOR-{node}-{sensor_type}",
        "sensor_type": sensor_type,
        "sensor_model": "MPU-6050",
        "generated_at": f"2026-11-16T10:00:0{n}.000+00:00",
        "priority": priority,
        "payload": {"x_g": 0.1, "y_g": 0.2, "z_g": 1.0, "rms_g": 1.0, "frequency_hz": 5.0},
    }


def test_un_agregado_por_nodo():
    lecturas = [lectura("NODE-FLOOR-2", n=1), lectura("NODE-FLOOR-1", n=2)]
    agregados = construir_agregados(lecturas, "SB-001", 30.0, 7, CATALOGO_POR_DEFECTO)
    assert len(agregados) == 2
    codigos = [a["bridges"][0]["node_code"] for a in agregados]
    assert codigos == ["NODE-FLOOR-1", "NODE-FLOOR-2"]  # orden estable por nodo


def test_prioridad_critica_gana_sobre_normal():
    lecturas = [lectura(priority="normal", n=1), lectura(priority="critical", n=2)]
    (agregado,) = construir_agregados(lecturas, "SB-001", 30.0, 1, CATALOGO_POR_DEFECTO)
    assert agregado["priority"] == "critical"
    assert agregado["quality"] == "anomaly"
    assert agregado["delivery_policy"] == "immediate"


def test_secuencia_y_ventana_se_conservan():
    lecturas = [lectura(n=1), lectura(n=3)]
    (agregado,) = construir_agregados(lecturas, "SB-001", 30.0, 42, CATALOGO_POR_DEFECTO)
    assert agregado["sequence_number"] == 42
    assert agregado["window"]["start"] < agregado["window"]["end"]
    assert agregado["window"]["sample_count"] == 2


def test_nodo_desconocido_falla():
    with pytest.raises(ValueError, match="Nodo desconocido"):
        construir_agregados([lectura("NODE-X")], "SB-001", 30.0, 1, CATALOGO_POR_DEFECTO)


def test_catalogo_por_defecto_sin_configuracion():
    assert cargar_catalogo(None) == CATALOGO_POR_DEFECTO
    assert cargar_catalogo("") == CATALOGO_POR_DEFECTO


def test_catalogo_desde_json():
    texto = json.dumps({"NODE-X": {"zone_id": "Z", "floor": 3, "bridge_name": "B3"}})
    assert set(cargar_catalogo(texto)) == {"NODE-X"}


def test_catalogo_rechaza_nodo_incompleto():
    with pytest.raises(ValueError, match="sin campos"):
        cargar_catalogo(json.dumps({"NODE-X": {"floor": 3}}))
