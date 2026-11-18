import tempfile
import unittest
from pathlib import Path

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


class BridgeServiceTest(unittest.TestCase):
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
                self.assertEqual(service.last_sync, "lora_backup")
                self.assertEqual(fake.sent, 1)
                self.assertEqual(len(service.store.pending_summaries()), 1)

                periodic = service.ingest([accelerometer_event(True)], 30.0)
                self.assertEqual(periodic["delivery_policy"], "periodic")
                self.assertEqual(fake.sent, 1, "La misma emergencia no debe saturar LoRa")
                self.assertEqual(len(service.store.pending_summaries()), 2)
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
