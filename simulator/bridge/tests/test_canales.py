import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.datos.canales.lora_virtual import LoraCanal
from app.datos.canales.rest_client import RestClient
from app.negocio.resumen_lora import construir_resumen_lora


class ServidorFalso:
    """Servidor HTTP mínimo que guarda la última petición y responde con el código dado."""

    def __init__(self, status: int) -> None:
        self.status = status
        self.ultima = {}
        servidor = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                largo = int(self.headers.get("Content-Length", "0"))
                servidor.ultima = {
                    "path": self.path,
                    "token": self.headers.get("X-Node-Token"),
                    "body": json.loads(self.rfile.read(largo)),
                }
                cuerpo = b'{"ok":true}' if servidor.status < 300 else b"fallo"
                self.send_response(servidor.status)
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *args):
                pass

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}"
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

    def cerrar(self):
        self._http.shutdown()
        self._http.server_close()


@pytest.fixture
def servidor_ok():
    s = ServidorFalso(202)
    yield s
    s.cerrar()


def test_rest_envia_con_token_del_nodo(servidor_ok):
    cliente = RestClient(servidor_ok.url, "/telemetry/aggregate", timeout=5)
    ok, detalle = cliente.enviar({"message_uid": "u1"}, token="secreto")
    assert ok is True
    assert servidor_ok.ultima["path"] == "/telemetry/aggregate"
    assert servidor_ok.ultima["token"] == "secreto"
    assert servidor_ok.ultima["body"] == {"message_uid": "u1"}


def test_rest_reporta_error_http():
    s = ServidorFalso(500)
    try:
        ok, detalle = RestClient(s.url, "/x", timeout=5).enviar({}, token="t")
    finally:
        s.cerrar()
    assert ok is False
    assert "500" in detalle  # urllib lanza HTTPError: detalle = str(exc), como el original


def test_rest_reporta_servidor_caido():
    ok, detalle = RestClient("http://127.0.0.1:9", "/x", timeout=1).enviar({}, token="t")
    assert ok is False and detalle


def test_rest_sin_url_no_esta_configurado():
    assert RestClient(None, "/x", timeout=1).configurado is False


def test_lora_entrega_sin_perdida():
    canal = LoraCanal(loss_rate=0, min_delay_ms=0, max_delay_ms=0, max_payload_bytes=1200, seed=1)
    resultado = canal.transmitir_resumen({"message_uid": "u1"})
    assert resultado.success is True
    assert resultado.reason == "ack_received"


def test_lora_rechaza_payload_grande():
    canal = LoraCanal(loss_rate=0, min_delay_ms=0, max_delay_ms=0, max_payload_bytes=10, seed=1)
    resultado = canal.transmitir_resumen({"message_uid": "u1" * 20})
    assert resultado.success is False
    assert resultado.reason == "payload_too_large"


def test_resumen_normal_es_telemetria_offline():
    agregado = {"schema_version": "1.0", "message_uid": "u", "building_code": "SB-001",
                "generated_at": "t", "sequence_number": 1, "priority": "normal",
                "bridges": [], "sensores_extra": "ignorado"}
    resumen = construir_resumen_lora(agregado)
    assert resumen["message_type"] == "telemetry_summary"
    assert resumen["delivery_status"] == "offline_summary"
    assert "sensores_extra" not in resumen


def test_resumen_critico_es_evento_de_emergencia():
    agregado = {"schema_version": "1.0", "message_uid": "u", "building_code": "SB-001",
                "generated_at": "t", "sequence_number": 1, "priority": "critical", "bridges": []}
    resumen = construir_resumen_lora(agregado)
    assert resumen["message_type"] == "emergency_event"
    assert resumen["delivery_status"] == "emergency"
