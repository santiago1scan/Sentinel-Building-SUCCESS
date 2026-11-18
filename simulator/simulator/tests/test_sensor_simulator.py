import unittest

from app.datos.generadores.virtual_sensors import SensorSimulator


class SensorSimulatorTest(unittest.TestCase):
    def test_generates_four_physical_sensor_models_without_storage(self) -> None:
        simulator = SensorSimulator(seed=7)
        events = simulator.generate_window("NODE-FLOOR-1", 1, 1.0, set())
        self.assertEqual(
            {event["sensor_model"] for event in events},
            {"ADXL355", "AMG8833", "BME688", "INA219"},
        )
        self.assertTrue(all("payload" in event for event in events))
        self.assertFalse(hasattr(simulator, "store"))

    def test_immediate_alarm_uses_a_zero_wait_raw_event(self) -> None:
        event = SensorSimulator(seed=8).generate_immediate_alert(
            "NODE-FLOOR-2", 2, "accelerometer"
        )
        self.assertEqual(event["priority"], "critical")
        self.assertEqual(event["quality"], "simulated_anomaly")
        self.assertGreaterEqual(event["payload"]["rms_g"], 0.25)


if __name__ == "__main__":
    unittest.main()
