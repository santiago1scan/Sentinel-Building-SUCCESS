from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

SIMULATOR_ROOT = Path(__file__).resolve().parents[2]
if str(SIMULATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_ROOT))

from bridge.bridge_service import BridgeRuntime, BridgeStore  # noqa: E402


class BackendHandler(BaseHTTPRequestHandler):
    received: list[dict] = []
    errors: list[str] = []

    def do_POST(self) -> None:  # noqa: N802
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.received.append(payload)
        if self.errors:
            response = {"message_uid": payload["message_uid"], "errors": self.errors}
        else:
            response = {
                "message_uid": payload["message_uid"],
                "readings_created": sum(len(bridge["sensors"]) for bridge in payload["bridges"]),
                "errors": [],
            }
        encoded = json.dumps(response).encode()
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        pass


class BridgeRestReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        BackendHandler.received = []
        BackendHandler.errors = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), BackendHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.temp_dir = TemporaryDirectory()
        self.store = BridgeStore(Path(self.temp_dir.name) / "bridge_local.db")
        self.runtime = BridgeRuntime.__new__(BridgeRuntime)
        self.runtime.args = SimpleNamespace(
            api_url=f"http://127.0.0.1:{self.server.server_port}",
            api_path="/telemetry/aggregate",
            api_token=None,
            api_timeout=2,
        )
        self.runtime.store = self.store

    def tearDown(self) -> None:
        self.store.close()
        self.temp_dir.cleanup()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()

    def save_pending(self, uid: str) -> None:
        self.store.save_aggregate({
            "message_uid": uid,
            "generated_at": uid,
            "bridges": [{"sensors": [{"sensor_code": "ADXL355-NODE-FLOOR-1"}]}],
        })

    def test_replays_pending_aggregates_in_order_after_backend_returns(self) -> None:
        self.save_pending("first")
        self.save_pending("second")

        sent = self.runtime._send_rest_pending()

        self.assertEqual(sent, ["first", "second"])
        self.assertEqual(
            [payload["message_uid"] for payload in BackendHandler.received],
            ["first", "second"],
        )
        self.assertEqual(self.store.pending(), [])

    def test_keeps_aggregate_pending_when_backend_reports_processing_errors(self) -> None:
        BackendHandler.errors = ["sensor not registered"]
        self.save_pending("pending")

        sent = self.runtime._send_rest_pending()

        self.assertEqual(sent, [])
        self.assertEqual([row[0] for row in self.store.pending()], ["pending"])
