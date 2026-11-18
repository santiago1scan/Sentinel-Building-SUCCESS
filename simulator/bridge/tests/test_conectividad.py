from app.negocio.conectividad import ServicioConectividad


class RestFalso:
    def __init__(self, configurado=True, alcanzable=True):
        self.configurado = configurado
        self.alcanzable = alcanzable
        self.sondeos = 0

    def sondear(self):
        self.sondeos += 1
        return self.alcanzable, "HTTP 200" if self.alcanzable else "sin ruta"


def servicio(rest, mqtt, reloj=lambda: 0.0):
    return ServicioConectividad(rest=rest, estado_mqtt=lambda: mqtt, reloj=reloj)


def test_en_linea_cuando_responden_todos_los_canales():
    assert servicio(RestFalso(), {"N1": True}).estado()["estado"] == "en_linea"


def test_parcial_si_solo_responde_uno():
    estado = servicio(RestFalso(alcanzable=False), {"N1": True}).estado()
    assert estado["estado"] == "parcial" and estado["canales_activos"] == 1 and estado["canales_total"] == 2


def test_sin_conexion_si_no_responde_ninguno():
    assert servicio(RestFalso(alcanzable=False), {"N1": False}).estado()["estado"] == "sin_conexion"


def test_sin_canales_configurados_es_sin_conexion():
    estado = servicio(RestFalso(configurado=False), {}).estado()
    assert estado["estado"] == "sin_conexion" and estado["backend"]["configurado"] is False


def test_el_sondeo_se_reutiliza_unos_segundos():
    rest, t = RestFalso(), [0.0]
    s = servicio(rest, {}, reloj=lambda: t[0])
    s.estado(); s.estado()
    assert rest.sondeos == 1
    t[0] = 9.0
    s.estado()
    assert rest.sondeos == 2


def test_endpoint_publico_y_pagina_con_el_componente(cliente):
    cuerpo = cliente.get("/api/conectividad").json()
    assert cuerpo["estado"] == "sin_conexion"  # el fixture no tiene REST ni MQTT
    assert 'id="red"' in cliente.get("/").text
    assert 'id="red"' in cliente.get("/perfil").text
    assert cliente.get("/static/js/red.js").status_code == 200


from datetime import datetime, timedelta, timezone

AHORA = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def hace(segundos):
    return (AHORA - timedelta(seconds=segundos)).isoformat()


def con_entregas(ultimas, rest=None, mqtt=None):
    return ServicioConectividad(rest=rest or RestFalso(), estado_mqtt=lambda: mqtt or {"N1": True},
                                ultimas_entregas=lambda: ultimas, ahora=lambda: AHORA)


def test_en_uso_es_el_canal_de_la_entrega_mas_reciente():
    estado = con_entregas({"rest": hace(20), "mqtt": hace(5)}).estado()

    assert estado["en_uso"] == "mqtt"
    assert estado["canales"]["mqtt"]["en_uso"] is True and estado["canales"]["rest"]["en_uso"] is False


def test_sin_entregas_recientes_no_hay_canal_en_uso():
    assert con_entregas({"rest": hace(600)}).estado()["en_uso"] is None
    assert con_entregas({}).estado()["en_uso"] is None


def test_lora_en_uso_cuando_solo_el_respaldo_entrega():
    estado = con_entregas({"lora": hace(10)}, rest=RestFalso(alcanzable=False), mqtt={"N1": False}).estado()

    assert estado["en_uso"] == "lora" and estado["estado"] == "sin_conexion"
