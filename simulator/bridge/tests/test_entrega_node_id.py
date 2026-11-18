"""La identidad del nodo en el backend es su node_id; el código es solo una etiqueta."""

from types import SimpleNamespace

from app.core.config import parse_node_ids
from app.datos.canales.mqtt_nodos import topico_nodo, usuario_mqtt
from app.negocio.entrega import Entregador


class OutboxFalso:
    def __init__(self):
        self.intentos = []
        self.enviados = []

    def mark_attempt(self, uid, detalle):
        self.intentos.append((uid, detalle))

    def mark_sent(self, uid, estado, detalle):
        self.enviados.append(uid)


class RestFalso:
    configurado = True

    def __init__(self):
        self.enviado = None

    def enviar(self, payload, token):
        self.enviado = (payload, token)
        return True, "ok"


def agregado(codigo="NODE-FLOOR-1"):
    return {"message_uid": "u1", "bridges": [{"node_code": codigo, "sensors": []}]}


def entregador(node_ids, tokens=None, rest=None):
    outbox = OutboxFalso()
    rest = rest or RestFalso()
    ent = Entregador(outbox=outbox, bitacora=SimpleNamespace(log=lambda *a: None), rest=rest,
                     enlaces={}, tokens=tokens if tokens is not None else {"NODE-FLOOR-1": "tok"},
                     node_ids=node_ids, lora=None)
    return ent, outbox, rest


def test_topico_y_usuario_usan_el_node_id():
    assert topico_nodo("SB-001", 7) == "sentinel/v1/SB-001/7/telemetry/aggregate"
    assert usuario_mqtt(7) == "node-7"


def test_rest_envia_el_node_id_en_cada_bridge():
    ent, outbox, rest = entregador({"NODE-FLOOR-1": 7})

    assert ent.enviar_rest("u1", agregado()) is True
    assert rest.enviado[0]["bridges"][0]["node_id"] == 7
    assert rest.enviado[0]["bridges"][0]["node_code"] == "NODE-FLOOR-1"  # la etiqueta sigue yendo


def test_rest_no_envia_si_el_nodo_no_tiene_node_id():
    ent, outbox, rest = entregador({})

    assert ent.enviar_rest("u1", agregado()) is False
    assert rest.enviado is None
    assert outbox.intentos == [("u1", "sin node_id para NODE-FLOOR-1")]


def test_el_node_id_llega_aunque_el_nodo_se_registre_despues_de_encolar():
    node_ids: dict[str, int] = {}
    ent, _, rest = entregador(node_ids)
    mensaje = agregado()
    assert ent.enviar_rest("u1", mensaje) is False

    node_ids["NODE-FLOOR-1"] = 9  # el registro termina

    assert ent.enviar_rest("u1", mensaje) is True
    assert rest.enviado[0]["bridges"][0]["node_id"] == 9


def test_parse_node_ids():
    assert parse_node_ids("NODE-FLOOR-1=5, NODE-FLOOR-2=6") == {"NODE-FLOOR-1": 5, "NODE-FLOOR-2": 6}
    assert parse_node_ids(None) == {}
