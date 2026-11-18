from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from simulator_v2.credentials import NodeRegistryStore
from simulator_v2.gateway import ExternalReceiver
from simulator_v2.registro import ConsultaClient, RegistrationService, RegistroError

NODES = ("NODE-FLOOR-1", "NODE-FLOOR-2")


class FakeConsulta(BaseHTTPRequestHandler):
    """Consulta simulada: POST /registrations y GET /registrations/{id} con X-Poll-Secret."""

    approved = False
    requests: list[dict] = []
    collected = 0

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["zone_id"] == 999:
            self._send(404, {"detail": "Zone not found"})
            return
        FakeConsulta.requests.append(body)
        self._send(202, {"registration_id": "reg-1", "poll_secret": "secreto",
                         "expires_at": "2030-01-01T00:00:00Z"})

    def do_GET(self) -> None:  # noqa: N802
        if self.headers.get("X-Poll-Secret") != "secreto":
            self._send(404, {"detail": "not found"})
        elif not FakeConsulta.approved:
            self._send(202, {"status": "pending"})
        elif FakeConsulta.collected:
            self._send(410, {"detail": "token ya entregado"})
        else:
            FakeConsulta.collected += 1
            self._send(200, {"token": "token-del-nodo", "node_id": 7})

    def log_message(self, *_args: object) -> None:
        pass


class RegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeConsulta.approved, FakeConsulta.requests, FakeConsulta.collected = False, [], 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeConsulta)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = NodeRegistryStore(Path(self.tmp.name) / "node_credentials.json")
        url = f"http://127.0.0.1:{self.server.server_port}"
        self.service = RegistrationService(self.store, ConsultaClient(url), NODES)

    def test_full_flow_stores_token_and_hides_secrets(self) -> None:
        state = self.service.request("NODE-FLOOR-1", "Beta - Piso 1", 1, 1)
        self.assertEqual(state["registro"]["status"], "pending")
        self.assertNotIn("poll_secret", state["registro"])
        self.assertEqual(FakeConsulta.requests[0]["code"], "NODE-FLOOR-1")
        self.assertEqual(FakeConsulta.requests[0]["sensors"], [
            {"code": "ADXL355-NODE-FLOOR-1", "sensor_type_id": 1},
            {"code": "AMG8833-NODE-FLOOR-1", "sensor_type_id": 2},
            {"code": "BME688-NODE-FLOOR-1", "sensor_type_id": 3},
            {"code": "INA219-NODE-FLOOR-1", "sensor_type_id": 4},
        ])
        self.assertEqual(len(state["sensores"]), 4)

        self.assertEqual(self.service.poll("NODE-FLOOR-1")["registro"]["status"], "pending")
        FakeConsulta.approved = True
        state = self.service.poll("NODE-FLOOR-1")
        self.assertTrue(state["registrado"])
        self.assertEqual(state["registro"]["status"], "delivered")
        self.assertEqual(self.store.token_for("NODE-FLOOR-1"), "token-del-nodo")
        self.assertEqual(self.store.get_request("NODE-FLOOR-1")["poll_secret"], "")
        self.assertNotIn("token-del-nodo", json.dumps(state))
        self.assertEqual(oct(self.store.path.stat().st_mode & 0o777), "0o600")

    def test_background_poll_collects_the_token_without_a_browser(self) -> None:
        import time
        from dashboard_react_v2.auth_web import AuthWeb, FirebaseSettings

        self.service.request("NODE-FLOOR-1", "Piso 1", 1, 1)
        FakeConsulta.approved = True
        AuthWeb(self.service, FirebaseSettings()).start_background_poll(interval_s=0.05)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.store.has_credential("NODE-FLOOR-1"):
            time.sleep(0.05)
        self.assertEqual(self.store.token_for("NODE-FLOOR-1"), "token-del-nodo")

    def test_nodes_register_independently(self) -> None:
        self.service.request("NODE-FLOOR-1", "Piso 1", 1, 1)
        self.assertFalse(self.service.status("NODE-FLOOR-2")["registrado"])
        self.assertIsNone(self.service.status("NODE-FLOOR-2")["registro"])

    def test_rejects_duplicates_unknown_nodes_and_backend_errors(self) -> None:
        self.service.request("NODE-FLOOR-1", "Piso 1", 1, 1)
        with self.assertRaises(RegistroError) as pending:
            self.service.request("NODE-FLOOR-1", "Piso 1", 1, 1)
        self.assertEqual(pending.exception.http_status, 409)
        with self.assertRaises(RegistroError) as unknown:
            self.service.request("NODE-OTRO", "x", 1, 1)
        self.assertEqual(unknown.exception.http_status, 404)
        with self.assertRaises(RegistroError) as zone:
            self.service.request("NODE-FLOOR-2", "Piso 2", 1, 999)
        self.assertEqual(zone.exception.http_status, 404)

    def test_requires_consulta_url(self) -> None:
        service = RegistrationService(self.store, ConsultaClient(""), NODES)
        with self.assertRaises(RegistroError) as error:
            service.request("NODE-FLOOR-1", "Piso 1", 1, 1)
        self.assertEqual(error.exception.http_status, 503)

    def test_registered_token_overrides_environment_token(self) -> None:
        receiver = ExternalReceiver(
            Path(self.tmp.name), node_tokens={"NODE-FLOOR-1": "del-entorno"}, credentials=self.store)
        self.addCleanup(receiver.close)
        self.assertEqual(receiver.token_for("NODE-FLOOR-1"), "del-entorno")
        self.store.save_credential("NODE-FLOOR-1", 7, "del-registro")
        self.assertEqual(receiver.token_for("NODE-FLOOR-1"), "del-registro")
        self.assertEqual(receiver.token_for("NODE-FLOOR-2"), "")


if __name__ == "__main__":
    unittest.main()
