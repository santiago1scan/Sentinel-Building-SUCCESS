from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from beta_simulator.sensors import SensorSimulator
from simulator_v2.bridge import PhysicalBetaBridge, SimulatedRadio
from simulator_v2.backend_contract import telemetry_endpoint, validate_backend_ack
from simulator_v2.gateway import ExternalReceiver
from simulator_v2.storage import SummaryStore


def summary(uid: str, when: str, node: str = "NODE-FLOOR-1", filler: str = "") -> dict:
    return {
        "schema_version": "2.0",
        "message_uid": uid,
        "message_type": "telemetry_aggregate",
        "building_uid": "SB-001",
        "building_code": "SB-001",
        "generated_at": when,
        "sent_at": None,
        "sequence_number": 1,
        "priority": "normal",
        "quality": "valid",
        "delivery_policy": "periodic",
        "delivery_status": "pending",
        "transport": "pending",
        "window": {"start": when, "end": when, "duration_seconds": 30, "sample_count": 1},
        "bridges": [{"node_code": node, "sensors": [], "notes": filler}],
    }


class SimulatorResilienceTests(unittest.TestCase):
    def test_anomaly_creates_and_routes_immediate_priority_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            bridge = PhysicalBetaBridge(
                "NODE-FLOOR-1", root / "bridge", receiver, radio,
                SensorSimulator(seed=13), backend_url="http://backend.local",
                node_token="node-1-token",
            )
            sent: list[dict] = []
            bridge._send_rest = lambda aggregate: (sent.append(aggregate) or True, "HTTP 202")  # type: ignore[method-assign]

            payload = bridge.run_immediate_alert("accelerometer")

            self.assertEqual(len(sent), 1)
            self.assertEqual(payload["priority"], "critical")
            self.assertEqual(payload["delivery_policy"], "immediate")
            self.assertEqual(payload["window"]["duration_seconds"], 0.0)
            self.assertEqual(len(payload["bridges"][0]["sensors"]), 1)
            self.assertEqual(payload["bridges"][0]["sensors"][0]["sensor_model"], "ADXL355")
            self.assertEqual(bridge.store.status()["pending"], 0)
            bridge.close()
            receiver.close()

    def test_offline_anomaly_is_sent_to_lora_immediately_and_kept_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            bridge = PhysicalBetaBridge(
                "NODE-FLOOR-1", root / "bridge", receiver, radio,
                SensorSimulator(seed=17),
            )
            bridge.network_up = False

            bridge.run_immediate_alert("accelerometer")

            self.assertEqual(receiver.received, 1)
            pending = bridge.store.pending_summaries()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["delivery_status"], "pending_backend")
            bridge.close()
            receiver.close()

    def test_alert_clear_is_published_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            bridge = PhysicalBetaBridge(
                "NODE-FLOOR-1", root / "bridge", receiver, radio,
                SensorSimulator(seed=19), backend_url="http://backend.local",
                node_token="node-1-token",
            )
            sent: list[dict] = []
            bridge._send_rest = lambda aggregate: (sent.append(aggregate) or True, "HTTP 202")  # type: ignore[method-assign]
            bridge.run_immediate_alert("accelerometer")

            clear = bridge.run_immediate_clear("accelerometer")

            self.assertEqual(len(sent), 2)
            self.assertEqual(clear["priority"], "normal")
            self.assertEqual(clear["delivery_policy"], "immediate")
            self.assertEqual(clear["quality"], "valid")
            self.assertNotIn("accelerometer", bridge.anomalies)
            bridge.close()
            receiver.close()

    def test_backend_endpoint_accepts_base_or_full_url(self) -> None:
        self.assertEqual(
            telemetry_endpoint("http://127.0.0.1:8089"),
            "http://127.0.0.1:8089/telemetry/aggregate",
        )
        self.assertEqual(
            telemetry_endpoint("http://127.0.0.1:8089/telemetry/aggregate"),
            "http://127.0.0.1:8089/telemetry/aggregate",
        )

    def test_backend_ack_requires_matching_uid_no_errors_and_all_readings(self) -> None:
        valid = '{"message_uid":"m-1","readings_created":4,"errors":[]}'
        self.assertTrue(validate_backend_ack(202, valid, "m-1", 4)[0])

        with_errors = '{"message_uid":"m-1","readings_created":3,"errors":["missing sensor"]}'
        self.assertFalse(validate_backend_ack(202, with_errors, "m-1", 4)[0])

        wrong_uid = '{"message_uid":"other","readings_created":4,"errors":[]}'
        self.assertFalse(validate_backend_ack(202, wrong_uid, "m-1", 4)[0])

        partial = '{"message_uid":"m-1","readings_created":2,"errors":[]}'
        self.assertFalse(validate_backend_ack(202, partial, "m-1", 4)[0])

    def test_duplicate_message_uid_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SummaryStore(Path(tmp) / "node.db")
            payload = summary("same-id", "2026-11-11T10:00:00+00:00")
            self.assertTrue(store.save_summary(payload, "NODE-FLOOR-1"))
            self.assertFalse(store.save_summary(payload, "NODE-FLOOR-1"))
            self.assertEqual(store.status()["summaries"], 1)
            store.close()

    def test_rotation_removes_delivered_but_protects_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SummaryStore(Path(tmp) / "node.db")
            first = summary("sent-id", "2026-11-11T10:00:00+00:00", filler="x" * 5000)
            pending = summary("pending-id", "2026-11-11T10:01:00+00:00", filler="y" * 5000)
            store.save_summary(first, "NODE-FLOOR-1")
            store.mark_summary("sent-id", "sent_rest", "HTTP 202")
            store.save_summary(pending, "NODE-FLOOR-1")
            store.limit_bytes = store.used_bytes() + 100
            newer = summary("new-id", "2026-11-11T10:02:00+00:00", filler="z" * 5000)
            store.save_summary(newer, "NODE-FLOOR-1")
            ids = {item["message_uid"] for item in store.pending_summaries()}
            self.assertIn("pending-id", ids)
            self.assertNotIn("sent-id", ids)
            store.close()

    def test_pending_is_replayed_after_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            node = "NODE-FLOOR-1"
            radio.online[node] = False
            bridge = PhysicalBetaBridge(
                node, root / "bridge", receiver, radio, SensorSimulator(seed=7)
            )
            bridge.network_up = False
            bridge.run_window(1)
            self.assertEqual(bridge.store.status()["pending"], 1)

            bridge.network_up = True
            bridge._send_rest = lambda aggregate: (True, "HTTP 202")  # type: ignore[method-assign]
            self.assertEqual(bridge.replay_pending(), 1)
            self.assertEqual(bridge.store.status()["pending"], 0)
            self.assertEqual(bridge.store.status()["summaries"], 1)
            bridge.close()
            receiver.close()

    def test_lora_backup_remains_pending_until_backend_acknowledges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            bridge = PhysicalBetaBridge(
                "NODE-FLOOR-1", root / "bridge", receiver, radio,
                SensorSimulator(seed=9),
            )

            bridge.network_up = False
            bridge.run_window(1)
            self.assertEqual(receiver.received, 1)
            self.assertEqual(bridge.store.status()["pending"], 1)
            self.assertEqual(
                bridge.store.pending_summaries()[0]["delivery_status"],
                "pending_backend",
            )

            # Replaying without a backend must not transmit another LoRa copy.
            self.assertEqual(bridge.replay_pending(), 0)
            self.assertEqual(receiver.received, 1)

            bridge._send_rest = lambda aggregate: (True, "HTTP 202")  # type: ignore[method-assign]
            self.assertEqual(bridge.replay_pending(), 1)
            self.assertEqual(bridge.store.status()["pending"], 0)
            bridge.close()
            receiver.close()

    def test_lora_is_not_used_while_internet_is_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receiver = ExternalReceiver(root / "receiver")
            radio = SimulatedRadio(receiver)
            bridge = PhysicalBetaBridge(
                "NODE-FLOOR-1", root / "bridge", receiver, radio,
                SensorSimulator(seed=11),
            )

            bridge.network_up = True
            bridge.run_window(1)
            self.assertEqual(receiver.received, 0)
            self.assertEqual(bridge.store.status()["pending"], 1)
            self.assertEqual(
                bridge.store.pending_summaries()[0]["delivery_status"],
                "pending",
            )
            bridge.close()
            receiver.close()


if __name__ == "__main__":
    unittest.main()
