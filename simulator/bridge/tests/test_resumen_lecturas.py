from datetime import datetime, timedelta, timezone

from tests.test_ingesta import lectura


def con_hora(evento, hora):
    return {**evento, "generated_at": hora.isoformat(timespec="milliseconds")}


def test_nodo_sin_lecturas_lo_dice_y_no_tiene_ultima(cliente):
    cuerpo = cliente.get("/api/lecturas/resumen?minutos=60").json()

    assert cuerpo == {"nodo": "NODE-FLOOR-1", "minutos": 60, "lecturas": 0, "ultima_lectura": None}


def test_lecturas_viejas_no_cuentan_en_la_ventana_pero_se_informa_la_ultima(cliente):
    vieja = datetime.now(timezone.utc) - timedelta(hours=3)
    cliente.post("/v1/readings", json=[con_hora(lectura("e1"), vieja)])

    cuerpo = cliente.get("/api/lecturas/resumen?minutos=60").json()

    assert cuerpo["lecturas"] == 0
    assert cuerpo["ultima_lectura"] == vieja.isoformat(timespec="milliseconds")


def test_lecturas_recientes_se_cuentan(cliente):
    ahora = datetime.now(timezone.utc)
    cliente.post("/v1/readings", json=[con_hora(lectura("e1"), ahora), con_hora(lectura("e2"), ahora)])

    assert cliente.get("/api/lecturas/resumen?minutos=60").json()["lecturas"] == 2


def test_solo_cuenta_las_lecturas_del_nodo_de_este_bridge(cliente):
    ahora = datetime.now(timezone.utc)
    cliente.post("/v1/readings", json=[con_hora(lectura("e1", node="NODE-FLOOR-2"), ahora)])

    assert cliente.get("/api/lecturas/resumen?minutos=60").json()["lecturas"] == 0


def test_la_pagina_de_inicio_usa_el_resumen(cliente):
    html = cliente.get("/").text

    assert 'id="estadoPunto"' in html and "/api/lecturas/resumen" in html
