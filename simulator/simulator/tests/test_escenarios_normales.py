"""Escenarios normales (24-nov-2026) y valores normales dentro de los rangos de la base.

Los rangos son los de la semilla c3f8a2d6b9e1 de monolito-escucha. Si el simulador los rompe, cualquier incidencia
arrastra alertas de energía o movimiento y la regla de gravedad vuelve emergencia a todo (vela incluida).
"""
import random

import pytest

from app.negocio.escenarios.definiciones import ESCENARIOS
from app.negocio.generacion.lecturas import energia, acelerometro, gas_ambiental, termico
from app.negocio.generacion.sobres import eventos_nodo
from app.negocio.simulacion import ControladorSimulacion

# variable: (mínimo, máximo) normal de la base. IAQ y TVOC no alarman por debajo.
RANGOS = {
    "x_g": (-0.01, 0.01), "y_g": (-0.01, 0.01), "z_g": (0.99, 1.01), "rms_g": (0.0002, 0.0071),
    "frequency_hz": (3, 4),
    "average_c": (17, 26), "maximum_c": (17, 35), "hot_pixels": (0, 0),
    "temperature_c": (10, 31), "humidity_percent": (72.78, 94.48), "pressure_hpa": (815, 835),
    "iaq_index": (None, 100), "tvoc_ppb": (None, 500),
    "bus_voltage_v": (11, 12), "current_ma": (300, 500), "power_mw": (3300, 6000),
}
MUESTRAS = 200


def dentro(variable, valor):
    bajo, alto = RANGOS[variable]
    return (bajo is None or valor >= bajo) and valor <= alto


@pytest.mark.parametrize("generador", [acelerometro, termico, gas_ambiental, energia])
def test_valores_normales_quedan_dentro_de_los_rangos(generador):
    rng = random.Random(1)
    for _ in range(MUESTRAS):
        for variable, valor in generador(rng, None).items():
            if variable in RANGOS:
                assert dentro(variable, valor), f"{variable}={valor}"


def test_energia_normal_es_la_red_y_sin_bateria_baja():
    lectura = energia(random.Random(2), None)
    assert lectura["power_source"] == "main" and lectura["battery_low"] is False


def test_vela_solo_calienta_uno_o_dos_pixeles():
    rng = random.Random(3)
    for _ in range(MUESTRAS):
        lectura = termico(rng, "candle")
        assert lectura["maximum_c"] > 35
        assert 1 <= lectura["hot_pixels"] <= 2
        assert lectura["average_c"] <= 26  # el promedio no se sale: solo hay un punto caliente


def test_spray_solo_ensucia_el_aire():
    rng = random.Random(4)
    for _ in range(MUESTRAS):
        lectura = gas_ambiental(rng, "spray")
        assert 150 <= lectura["iaq_index"] <= 250
        assert 800 <= lectura["tvoc_ppb"] <= 2000
        for variable in ("temperature_c", "humidity_percent", "pressure_hpa"):
            assert dentro(variable, lectura[variable]), variable


def test_sensor_danado_manda_temperatura_imposible_y_lo_demas_normal():
    rng = random.Random(5)
    for _ in range(MUESTRAS):
        lectura = gas_ambiental(rng, "faulty")
        assert not -40 <= lectura["temperature_c"] <= 85  # fuera del rango físico del BME688
        for variable in ("humidity_percent", "pressure_hpa", "iaq_index", "tvoc_ppb"):
            assert dentro(variable, lectura[variable]), variable


def test_incendio_sigue_igual():
    rng = random.Random(6)
    termica, gas = termico(rng, "fire"), gas_ambiental(rng, "fire")
    assert termica["hot_pixels"] == 4 and termica["maximum_c"] >= 45
    assert gas["iaq_index"] >= 250 and gas["tvoc_ppb"] >= 900


def test_eventos_del_nodo_usan_el_modo_de_cada_sensor():
    eventos = eventos_nodo("NODE-FLOOR-1", 1, {"thermal_array": "candle"}, set(), random.Random(7))
    por_tipo = {e["sensor_type"]: e for e in eventos}
    assert 1 <= por_tipo["thermal_array"]["payload"]["hot_pixels"] <= 2
    assert por_tipo["thermal_array"]["quality"] == "simulated_anomaly"
    assert por_tipo["thermal_array"]["delivery_policy"] == "immediate"  # el bridge la manda de inmediato
    assert por_tipo["gas_environmental"]["quality"] == "valid"


def test_escenarios_nuevos_estan_definidos_con_su_modo():
    assert ESCENARIOS["candle"]["sensors"] == ("grideye",) and ESCENARIOS["candle"]["mode"] == "candle"
    assert ESCENARIOS["spray"]["sensors"] == ("bme688",) and ESCENARIOS["spray"]["mode"] == "spray"
    assert ESCENARIOS["faulty_sensor"]["sensors"] == ("bme688",)
    assert ESCENARIOS["faulty_sensor"]["mode"] == "faulty"
    assert ESCENARIOS["fire"]["mode"] == "fire"


class ClienteFalso:
    timeout = 1

    def enviar_lecturas(self, lecturas):
        return {}

    def estado(self):
        return None


@pytest.fixture
def controlador():
    return ControladorSimulacion(nodos=["NODE-FLOOR-1", "NODE-FLOOR-2"], intervalo_s=30, cliente=ClienteFalso())


@pytest.mark.parametrize("nombre", ["candle", "spray"])
def test_vela_y_spray_aceptan_todos_los_nodos(controlador, nombre):
    resultado = controlador.iniciar_escenario_desde({"scenario": nombre, "nodes": []})
    assert resultado == {"ok": False, "error": "Start the simulator before activating a scenario."}  # válido


@pytest.mark.parametrize("nodos", [[], ["NODE-FLOOR-1", "NODE-FLOOR-2"]])
def test_sensor_danado_exige_un_solo_nodo(controlador, nodos):
    with pytest.raises(ValueError):
        controlador.iniciar_escenario_desde({"scenario": "faulty_sensor", "nodes": nodos})


def test_escenario_de_vela_pone_el_modo_en_el_sensor(controlador):
    import time

    controlador._ejecutando = True  # sin el ciclo de envío: solo se mira el estado que deja el escenario
    assert controlador.iniciar_escenario("candle", ["NODE-FLOOR-1"], None)["ok"] is True
    limite = time.monotonic() + 2
    while not controlador._anomalias["NODE-FLOOR-1"] and time.monotonic() < limite:
        time.sleep(0.01)
    assert controlador._anomalias == {"NODE-FLOOR-1": {"thermal_array": "candle"}, "NODE-FLOOR-2": {}}
