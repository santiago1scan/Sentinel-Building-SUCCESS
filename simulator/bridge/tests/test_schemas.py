import pytest
from pydantic import ValidationError

from app.presentacion.schemas import extraer_lecturas


def lectura(**cambios):
    base = {
        "event_id": "evt-1",
        "event_type": "sensor_reading",
        "node_id": "NODE-FLOOR-1",
        "sensor_id": "SENSOR-1-ACC",
        "sensor_type": "accelerometer",
        "sensor_model": "MPU-6050",
        "generated_at": "2026-11-16T10:00:00.000+00:00",
        "priority": "normal",
        "payload": {"x_g": 0.1, "y_g": 0.2, "z_g": 1.0, "rms_g": 1.0, "frequency_hz": 5.0},
    }
    base.update(cambios)
    return base


def test_acepta_lista_directa():
    assert len(extraer_lecturas([lectura()])) == 1


def test_acepta_envoltura_readings():
    assert len(extraer_lecturas({"readings": [lectura(), lectura(event_id="evt-2")]})) == 2


def test_conserva_campos_extra_del_evento():
    (modelo,) = extraer_lecturas([lectura()])
    assert modelo.model_dump()["event_type"] == "sensor_reading"


def test_rechaza_readings_que_no_es_lista():
    with pytest.raises(ValueError, match="debe ser una lista"):
        extraer_lecturas({"readings": "nope"})


def test_rechaza_prioridad_desconocida():
    with pytest.raises(ValidationError):
        extraer_lecturas([lectura(priority="urgent")])


def test_rechaza_tipo_de_sensor_desconocido():
    with pytest.raises(ValidationError):
        extraer_lecturas([lectura(sensor_type="laser")])


def test_rechaza_lectura_sin_event_id():
    datos = lectura()
    del datos["event_id"]
    with pytest.raises(ValidationError):
        extraer_lecturas([datos])
