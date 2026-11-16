from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request

from beta_simulator.config import NODES
from beta_simulator.protocol import aggregate_for_bridge
from beta_simulator.sensors import SensorSimulator, utc_now
from simulator_v2.backend_contract import telemetry_endpoint, validate_backend_ack


BACKEND_URL = os.getenv("SENTINEL_INTEGRATION_BACKEND_URL")
TOKENS = {
    "NODE-FLOOR-1": os.getenv("SENTINEL_NODE_TOKEN_FLOOR_1"),
    "NODE-FLOOR-2": os.getenv("SENTINEL_NODE_TOKEN_FLOOR_2"),
}


@unittest.skipUnless(
    BACKEND_URL and all(TOKENS.values()),
    "real backend integration is opt-in and requires URL plus both node tokens",
)
class RealBackendIntegrationTests(unittest.TestCase):
    def test_each_bridge_is_accepted_with_its_own_token(self) -> None:
        simulator = SensorSimulator(seed=42)
        for sequence, node_code in enumerate(NODES, start=1):
            events = simulator.generate_window(node_code, sequence, 1.0, set())
            payload = aggregate_for_bridge(node_code, events, 1.0, sequence)
            payload["sent_at"] = utc_now()
            payload["delivery_status"] = "realtime"
            payload["transport"] = "rest"
            request = urllib.request.Request(
                telemetry_endpoint(BACKEND_URL or ""),
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Node-Token": TOKENS[node_code] or "",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    body = response.read().decode("utf-8")
                    accepted, detail = validate_backend_ack(
                        response.status,
                        body,
                        payload["message_uid"],
                        len(payload["bridges"][0]["sensors"]),
                    )
            except urllib.error.HTTPError as exc:
                self.fail(f"{node_code}: HTTP {exc.code}: {exc.read().decode('utf-8')}")
            self.assertTrue(accepted, f"{node_code}: {detail}")


if __name__ == "__main__":
    unittest.main()
