from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from beta_simulator.config import NODES
from beta_simulator.sensors import SensorSimulator

from .bridge import PhysicalBetaBridge, SimulatedRadio
from .credentials import NodeRegistryStore
from .gateway import ExternalReceiver


ALIASES = {
    "adxl355": "accelerometer",
    "amg8833": "thermal_array",
    "grideye": "thermal_array",
    "bme688": "gas_environmental",
    "ina219": "power_monitor",
}


def node_from_token(token: str) -> str:
    return "NODE-FLOOR-1" if token.endswith("1") else "NODE-FLOOR-2"


def command_loop(bridges, receiver, radio, stop) -> None:
    print("Commands: status, network down/up, bridge1 down/up, bridge2 down/up,")
    print("          lora1 down/up, lora2 down/up, anomaly <bridge1|bridge2> <sensor>, clear <bridge> <sensor>, quit")
    while not stop.is_set():
        try:
            parts = input("sim-v2> ").strip().lower().split()
        except (EOFError, KeyboardInterrupt):
            stop.set()
            return
        if not parts:
            continue
        if parts[0] == "quit":
            stop.set()
        elif parts[0] == "status":
            for bridge in bridges.values():
                print(bridge.status())
            print(receiver.status())
        elif parts[0] == "network" and len(parts) > 1:
            up = parts[1] == "up"
            receiver.network_up = up
            for bridge in bridges.values():
                bridge.network_up = up
            if up:
                replayed = sum(bridge.replay_pending() for bridge in bridges.values())
                print(f"network=UP | pending_replayed={replayed}")
                continue
            print(f"network={'UP' if up else 'DOWN'}")
        elif parts[0] in {"bridge1", "bridge2", "lora1", "lora2"} and len(parts) > 1:
            node = node_from_token(parts[0])
            up = parts[1] == "up"
            if parts[0].startswith("bridge"):
                bridges[node].online = up
            else:
                radio.online[node] = up
            print(f"{parts[0]}={'UP' if up else 'DOWN'}")
        elif parts[0] in {"anomaly", "clear"} and len(parts) >= 3:
            node = node_from_token(parts[1])
            sensor = ALIASES.get(parts[2], parts[2])
            if parts[0] == "anomaly":
                alert = bridges[node].run_immediate_alert(sensor)
                print(f"immediate_alert={alert['message_uid']}")
            else:
                clear = bridges[node].run_immediate_clear(sensor)
                print(f"immediate_clear={clear['message_uid']}")
            print(f"{node} anomalies={sorted(bridges[node].anomalies)}")


class ControlHandler(BaseHTTPRequestHandler):
    bridges = {}
    receiver = None
    radio = None
    stop = None

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/control/status":
            self._json(200, {
                "network_up": self.receiver.network_up,
                "bridges": {node: bridge.status() for node, bridge in self.bridges.items()},
                "lora": dict(self.radio.online),
            })
            return
        self._json(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/control":
            self._json(404, {"detail": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            command = json.loads(self.rfile.read(size).decode("utf-8"))
            action = command.get("action")
            target = command.get("target")
            value = command.get("value")
            if action == "network":
                up = bool(value)
                self.receiver.network_up = up
                for bridge in self.bridges.values():
                    bridge.network_up = up
                replayed = sum(bridge.replay_pending() for bridge in self.bridges.values()) if up else 0
            elif action == "bridge":
                self.bridges[target].online = bool(value)
                replayed = self.bridges[target].replay_pending() if bool(value) else 0
            elif action == "lora":
                self.radio.online[target] = bool(value)
            elif action == "anomaly":
                sensor = command.get("sensor")
                if bool(value):
                    alert = self.bridges[target].run_immediate_alert(sensor)
                else:
                    alert = self.bridges[target].run_immediate_clear(sensor)
            elif action == "stop":
                self.stop.set()
            else:
                self._json(400, {"detail": "Unsupported action"})
                return
            result = {"ok": True, "action": action, "target": target, "value": value,
                      "pending_replayed": replayed if action in {"network", "bridge"} else 0}
            if action == "anomaly":
                result["immediate_alert" if bool(value) else "immediate_clear"] = {
                    "message_uid": alert["message_uid"],
                    "priority": alert["priority"],
                    "generated_at": alert["generated_at"],
                    "delivery_status": self.bridges[target].last_sync,
                }
            self._json(200, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"detail": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"sim-control | {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel physical beta simulator v2")
    parser.add_argument("--window-seconds", type=float, default=30.0)
    parser.add_argument("--cycles", type=int, default=0, help="0 means continuous")
    parser.add_argument("--data-dir", default="data_simulation_v2")
    parser.add_argument("--backend-url", default=None, help="Base URL without /telemetry/aggregate")
    parser.add_argument(
        "--node-token-floor-1",
        default=os.getenv("SENTINEL_NODE_TOKEN_FLOOR_1"),
        help="NODE-FLOOR-1 token (or SENTINEL_NODE_TOKEN_FLOOR_1)",
    )
    parser.add_argument(
        "--node-token-floor-2",
        default=os.getenv("SENTINEL_NODE_TOKEN_FLOOR_2"),
        help="NODE-FLOOR-2 token (or SENTINEL_NODE_TOKEN_FLOOR_2)",
    )
    parser.add_argument("--lora-loss-rate", type=float, default=0.0)
    parser.add_argument("--storage-capacity-gb", type=float, default=128.0)
    parser.add_argument("--storage-limit-ratio", type=float, default=0.70)
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=8792)
    parser.add_argument("--no-input", action="store_true")
    args = parser.parse_args()
    if args.window_seconds <= 0:
        parser.error("window-seconds debe ser positivo")
    if not 0 <= args.lora_loss_rate <= 1:
        parser.error("lora-loss-rate debe estar entre 0 y 1")
    if not 0 < args.storage_limit_ratio <= 1:
        parser.error("storage-limit-ratio debe estar entre 0 y 1")
    root = Path(args.data_dir)
    node_tokens = {
        "NODE-FLOOR-1": args.node_token_floor_1 or "",
        "NODE-FLOOR-2": args.node_token_floor_2 or "",
    }
    credentials = NodeRegistryStore(root / "node_credentials.json")
    receiver = ExternalReceiver(
        root, backend_url=args.backend_url, node_tokens=node_tokens, credentials=credentials)
    radio = SimulatedRadio(receiver, loss_rate=args.lora_loss_rate)
    sensor_simulator = SensorSimulator(seed=42)
    bridges = {
        node: PhysicalBetaBridge(
            node, root, receiver, radio, sensor_simulator,
            backend_url=args.backend_url,
            node_token=node_tokens[node],
            capacity_gb=args.storage_capacity_gb,
            limit_ratio=args.storage_limit_ratio,
        )
        for node in NODES
    }

    stop = threading.Event()
    ControlHandler.bridges = bridges
    ControlHandler.receiver = receiver
    ControlHandler.radio = radio
    ControlHandler.stop = stop
    control_server = ThreadingHTTPServer((args.control_host, args.control_port), ControlHandler)
    threading.Thread(target=control_server.serve_forever, daemon=True).start()
    if not args.no_input:
        threading.Thread(target=command_loop, args=(bridges, receiver, radio, stop), daemon=True).start()
    print("Sentinel simulation v2 started")
    print("Architecture: two independent bridges | raw data in memory | summaries in SQLite | LoRa fallback")
    print(f"window={args.window_seconds}s | data={root} | backend={'configured' if args.backend_url else 'disabled'} | control=http://{args.control_host}:{args.control_port}")

    cycles = 0
    try:
        while not stop.is_set() and (args.cycles == 0 or cycles < args.cycles):
            cycles += 1
            for bridge in bridges.values():
                if bridge.online:
                    bridge.run_window(args.window_seconds)
                else:
                    print(f"{bridge.node_code} | bridge_down | no new readings")
            receiver.forward_pending()
            if args.cycles == 0:
                stop.wait(args.window_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        for bridge in bridges.values():
            bridge.close()
        receiver.close()
        control_server.shutdown()
        print("Simulation v2 stopped; summaries and synchronization logs remain in the data directory.")


if __name__ == "__main__":
    main()

