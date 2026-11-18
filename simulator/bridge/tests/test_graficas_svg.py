from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.presentacion.componentes.graficas_svg import _num, dibujar, hora_12

BOGOTA = ZoneInfo("America/Bogota")


def ts(hora, minuto=0):
    return datetime(2026, 11, 17, hora, minuto, tzinfo=timezone.utc).timestamp()


def test_hora_12_usa_am_pm_sin_cero_a_la_izquierda():
    assert hora_12(ts(0, 5)) == "12:05 AM"
    assert hora_12(ts(9, 30)) == "9:30 AM"
    assert hora_12(ts(12, 0)) == "12:00 PM"
    assert hora_12(ts(15, 5)) == "3:05 PM"
    assert hora_12(ts(23, 59)) == "11:59 PM"


def test_hora_12_respeta_la_zona_horaria():
    assert hora_12(ts(20, 0), BOGOTA) == "3:00 PM"  # UTC-5


def test_numeros_cortos_y_sin_notacion_cientifica():
    assert _num(1500.4) == "1500"
    assert _num(12.34) == "12.3"
    assert _num(0.25) == "0.25"
    assert _num(1.0) == "1"
    assert "e" not in _num(123456789.0)


def linea(puntos, zona="America/Bogota"):
    return {"titulo": "Energía · voltaje", "tipo": "linea", "minutos": 60, "unidad": "V", "zona": zona,
            "desde_ts": ts(19), "hasta_ts": ts(20), "puntos": puntos}


def test_el_eje_trae_cinco_horas_en_formato_12_y_la_zona_de_los_datos():
    svg = dibujar(linea([(ts(19, 30), 12.0), (ts(19, 50), 12.4)]))

    for esperado in ("2:00 PM", "2:15 PM", "2:30 PM", "2:45 PM", "3:00 PM"):
        assert esperado in svg
    assert "UTC" not in svg


def test_muestra_el_ultimo_valor_con_su_unidad_y_hora():
    svg = dibujar(linea([(ts(19, 30), 12.0), (ts(19, 50), 12.4)]))

    assert "12.4 V" in svg and "último valor · 2:50 PM" in svg


def test_zona_invalida_cae_a_utc_sin_romper():
    assert "7:00 PM" in dibujar(linea([(ts(19, 30), 1.0)], zona="No/Existe"))


def test_grafica_vacia_dice_que_no_hay_lecturas():
    assert "Sin lecturas en los últimos 60 min" in dibujar(linea([]))


def test_prioridad_usa_etiquetas_en_espanol():
    datos = {"titulo": "Prioridad", "tipo": "prioridad", "minutos": 60, "zona": "UTC",
             "desde_ts": ts(19), "hasta_ts": ts(20),
             "minutos_datos": [{"ts": ts(19, 10), "normal": 3, "high": 1, "critical": 0}]}
    svg = dibujar(datos)

    assert "Normal" in svg and "Alta" in svg and "Crítica" in svg
