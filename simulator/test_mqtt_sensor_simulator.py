from __future__ import annotations

import sqlite3
import threading
import unittest
from unittest.mock import patch

from mqtt_sensor_simulator import command_loop


class SimulatorCommandTests(unittest.TestCase):
    def test_clear_wakes_the_producer_to_publish_normal_readings(self) -> None:
        state = {
            "anomalies": {"NODE-FLOOR-1": {"thermal_array"}},
            "lock": threading.Lock(),
            "wake_event": threading.Event(),
        }
        stop = threading.Event()
        con = sqlite3.connect(":memory:")

        with patch("builtins.input", side_effect=[
            "clear NODE-FLOOR-1 grideye",
            "quit",
        ]):
            command_loop(state, con, stop)

        self.assertNotIn("thermal_array", state["anomalies"]["NODE-FLOOR-1"])
        self.assertTrue(state["wake_event"].is_set())
        con.close()


if __name__ == "__main__":
    unittest.main()
