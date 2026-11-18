import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.core.backend_contract import validate_backend_ack
from app.negocio.bridge_service import BridgeService


def accelerometer_event(anomaly: bool) -> dict:
    return {
        "node_code": "NODE-FLOOR-1",
        "sensor_type": "accelerometer",
        "generated_at": "2026-11-17T12:00:00+00:00",
        "priority": "critical" if anomaly else "normal",
        "quality": "simulated_anomaly" if anomaly else "valid",
        "payload": {
            "x_g": 0.1, "y_g": 0.1, "z_g": 1.0,
            "rms_g": 0.4 if anomaly else 0.01, "frequency_hz": 2.0,
        },
    }


class FakeRadio:
    def __init__(self) -> None:
        self.online = True
        self.acks = {}
        self.sent = 0

    def send(self, payload: dict) -> bool:
        self.sent += 1
        return True

    def close(self) -> None:
        return


class BackendHandler(BaseHTTPRequestHandler):
    received_path = ""
    received_token = ""
    received_payload: dict = {}

    def do_POST(self) -> None:  # noqa: N802
        size = int(self.headers.get("Content-Length", "0"))
        type(self).received_path = self.path
        type(self).received_token = self.headers.get("X-Node-Token", "")
        type(self).received_payload = json.loads(self.rfile.read(size))
        body = json.dumps({
            "message_uid": type(self).received_payload["message_uid"],
            "duplicate": False,
            "readings_created": 5,
            "alerts_opened": 0,
            "errors": [],
        }).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


class BridgeServiceTest(unittest.TestCase):
    def test_backend_real_contract_is_used(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as folder:
            service = BridgeService(
                "NODE-FLOOR-1", Path(folder),
                f"http://127.0.0.1:{server.server_address[1]}",
                "token-piso-1", "127.0.0.1", 19201, b"test-key",
            )
            service.radio.close()
            service.radio = FakeRadio()
            try:
                payload = service.ingest([accelerometer_event(False)], 30.0)
                self.assertEqual(BackendHandler.received_path, "/telemetry/aggregate")
                self.assertEqual(BackendHandler.received_token, "token-piso-1")
                self.assertEqual(BackendHandler.received_payload["message_uid"], payload["message_uid"])
                self.assertEqual(BackendHandler.received_payload["message_type"], "half_hour_summary")
                self.assertEqual(len(service.store.pending_summaries()), 0)
                self.assertEqual(service.last_sync, "rest")
            finally:
                service.close()
                server.shutdown()
                server.server_close()

    def test_duplicate_backend_ack_closes_pending_message(self) -> None:
        accepted, detail = validate_backend_ack(
            202,
            json.dumps({
                "message_uid": "same-message",
                "duplicate": True,
                "readings_created": 0,
                "errors": [],
            }),
            "same-message",
            4,
        )
        self.assertTrue(accepted)
        self.assertIn("already stored", detail)

    def test_lora_alert_is_parallel_and_backend_pending_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            service = BridgeService(
                "NODE-FLOOR-1", Path(folder), None, "", "127.0.0.1", 19200, b"test-key"
            )
            service.radio.close()
            fake = FakeRadio()
            service.radio = fake
            try:
                immediate = service.ingest([accelerometer_event(True)], 0.0)
                self.assertEqual(immediate["delivery_policy"], "immediate")
                self.assertEqual(immediate["message_type"], "out_of_range")
                self.assertIn("rms_g", immediate["bridges"][0]["sensors"][0]["data"])
                self.assertEqual(service.last_sync, "lora_backup")
                self.assertEqual(fake.sent, 1)
                self.assertEqual(len(service.store.pending_summaries()), 1)

                periodic = service.ingest([accelerometer_event(True)], 30.0)
                self.assertEqual(periodic["delivery_policy"], "periodic")
                self.assertEqual(periodic["message_type"], "half_hour_summary")
                self.assertIn("rms_g__avg", periodic["bridges"][0]["sensors"][0]["data"])
                self.assertEqual(fake.sent, 1, "La misma emergencia no debe saturar LoRa")
                self.assertEqual(len(service.store.pending_summaries()), 2)
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
