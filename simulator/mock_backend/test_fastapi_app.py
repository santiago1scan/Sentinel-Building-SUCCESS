from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import fastapi_app


class MockBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self.temp_dir.name)
        self.db_path = data_dir / "api_received.db"
        self.data_dir_patch = patch.object(fastapi_app, "DATA_DIR", data_dir)
        self.db_path_patch = patch.object(fastapi_app, "DB_PATH", self.db_path)
        self.token_patch = patch.object(fastapi_app, "API_TOKEN", "")
        self.data_dir_patch.start()
        self.db_path_patch.start()
        self.token_patch.start()

    def tearDown(self) -> None:
        self.token_patch.stop()
        self.db_path_patch.stop()
        self.data_dir_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def payload(schema_version: str, message_uid: str) -> dict:
        return {
            "schema_version": schema_version,
            "message_type": "telemetry_aggregate",
            "message_uid": message_uid,
            "priority": "normal",
            "bridges": [
                {"sensors": [{"sensor_code": "A"}, {"sensor_code": "B"}]}
            ],
        }

    def test_persists_both_simulator_contracts_and_returns_delivery_ack(self) -> None:
        for version in ("1.0", "2.0"):
            result = fastapi_app.receive_message(self.payload(version, f"uid-{version}"), None)
            self.assertEqual(result["readings_created"], 2)
            self.assertEqual(result["errors"], [])

        con = sqlite3.connect(self.db_path)
        try:
            count = con.execute("SELECT COUNT(*) FROM received_message").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(count, 2)

    def test_duplicate_is_acknowledged_without_inserting_again(self) -> None:
        payload = self.payload("2.0", "same-uid")
        fastapi_app.receive_message(payload, None)
        result = fastapi_app.receive_message(payload, None)

        self.assertTrue(result["duplicate"])
        self.assertEqual(result["readings_created"], 2)
        con = sqlite3.connect(self.db_path)
        try:
            count = con.execute("SELECT COUNT(*) FROM received_message").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(count, 1)

    def test_scenario_alarm_overrides_beta_until_scenario_sends_clear(self) -> None:
        now = datetime.now(timezone.utc)

        def sensor_payload(
            schema_version: str,
            message_uid: str,
            priority: str,
            generated_at: str,
            maximum_c: float,
        ) -> dict:
            payload = self.payload(schema_version, message_uid)
            payload.update(priority=priority, generated_at=generated_at)
            payload["bridges"] = [{
                "node_code": "NODE-FLOOR-1",
                "floor": 1,
                "sensors": [{
                    "sensor_code": "THERMAL-1",
                    "sensor_model": "Thermal",
                    "measurement_type": "temperature",
                    "data": {"maximum_c": maximum_c},
                }],
            }]
            return payload

        fastapi_app.receive_message(sensor_payload(
            "2.0", "beta-normal", "normal", now.isoformat(), 25
        ), None)
        fastapi_app.receive_message(sensor_payload(
            "1.0", "scenario-fire", "high", (now + timedelta(seconds=1)).isoformat(), 52
        ), None)
        fastapi_app.receive_message(sensor_payload(
            "2.0", "beta-after-fire", "normal", (now + timedelta(seconds=2)).isoformat(), 24
        ), None)

        con = fastapi_app.db()
        try:
            reading = fastapi_app.latest_sensor_readings(con)[0]
        finally:
            con.close()
        self.assertEqual(reading["source"], "scenario")
        self.assertEqual(reading["data"]["maximum_c"], 52)

        fastapi_app.receive_message(sensor_payload(
            "1.0", "scenario-clear", "normal", (now + timedelta(seconds=3)).isoformat(), 25
        ), None)
        con = fastapi_app.db()
        try:
            reading = fastapi_app.latest_sensor_readings(con)[0]
        finally:
            con.close()
        self.assertEqual(reading["source"], "scenario")
        self.assertEqual(reading["priority"], "normal")
        self.assertEqual(reading["data"]["maximum_c"], 25)

    def test_expired_scenario_alarm_does_not_override_live_beta_data(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        beta_payload = self.payload("2.0", "beta-live")
        beta_payload.update(generated_at=now, priority="normal")
        beta_payload["bridges"] = [{
            "node_code": "NODE-FLOOR-1",
            "floor": 1,
            "sensors": [{
                "sensor_code": "THERMAL-1",
                "sensor_model": "Thermal",
                "measurement_type": "temperature",
                "data": {"maximum_c": 25},
            }],
        }]
        scenario_payload = self.payload("1.0", "scenario-old-fire")
        scenario_payload.update(
            generated_at="2026-01-01T10:00:00+00:00",
            priority="high",
        )
        scenario_payload["bridges"] = [{
            "node_code": "NODE-FLOOR-1",
            "floor": 1,
            "sensors": [{
                "sensor_code": "THERMAL-1",
                "sensor_model": "Thermal",
                "measurement_type": "temperature",
                "data": {"maximum_c": 52},
            }],
        }]
        fastapi_app.receive_message(scenario_payload, None)
        fastapi_app.receive_message(beta_payload, None)

        con = fastapi_app.db()
        try:
            reading = fastapi_app.latest_sensor_readings(con)[0]
        finally:
            con.close()
        self.assertEqual(reading["source"], "beta")
        self.assertFalse(reading["stale"])
        self.assertEqual(reading["data"]["maximum_c"], 25)


if __name__ == "__main__":
    unittest.main()
