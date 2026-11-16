from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def wait_for(url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Service did not become ready: {url}")


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Sentinel Building Beta simulation")
    parser.add_argument("--window-seconds", type=float, default=30.0)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--dashboard-port", type=int, default=8782)
    parser.add_argument("--dashboard-host", default="127.0.0.1")
    parser.add_argument("--control-port", type=int, default=8790)
    parser.add_argument("--control-host", default="127.0.0.1")
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SENTINEL_BACKEND_URL"),
    )
    parser.add_argument(
        "--node-token-floor-1",
        default=os.getenv("SENTINEL_NODE_TOKEN_FLOOR_1"),
    )
    parser.add_argument(
        "--node-token-floor-2",
        default=os.getenv("SENTINEL_NODE_TOKEN_FLOOR_2"),
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    simulator_command = [
        sys.executable,
        "-u",
        "-m",
        "simulator_v2.run_simulation",
        "--data-dir",
        str(data_dir),
        "--window-seconds",
        str(args.window_seconds),
        "--storage-capacity-gb",
        "128",
        "--storage-limit-ratio",
        "0.70",
        "--control-port",
        str(args.control_port),
        "--control-host",
        args.control_host,
        "--no-input",
    ]
    if args.backend_url:
        if not args.node_token_floor_1 or not args.node_token_floor_2:
            parser.error("backend-url requires a token for NODE-FLOOR-1 and NODE-FLOOR-2")
        simulator_command.extend(["--backend-url", args.backend_url])

    simulator_env = os.environ.copy()
    if args.node_token_floor_1:
        simulator_env["SENTINEL_NODE_TOKEN_FLOOR_1"] = args.node_token_floor_1
    if args.node_token_floor_2:
        simulator_env["SENTINEL_NODE_TOKEN_FLOOR_2"] = args.node_token_floor_2

    dashboard_command = [
        sys.executable,
        "-u",
        "-m",
        "dashboard_react_v2.react_dashboard_server",
        "--data-dir",
        str(data_dir),
        "--port",
        str(args.dashboard_port),
        "--host",
        args.dashboard_host,
        "--control-url",
        f"http://127.0.0.1:{args.control_port}",
    ]

    # Tokens are inherited through the child environment instead of being
    # exposed in the process command line.
    simulator = subprocess.Popen(simulator_command, cwd=ROOT, env=simulator_env)
    dashboard = subprocess.Popen(dashboard_command, cwd=ROOT)
    dashboard_url = f"http://127.0.0.1:{args.dashboard_port}/"

    try:
        wait_for(f"http://127.0.0.1:{args.control_port}/api/control/status")
        wait_for(dashboard_url)
        print("\nSentinel Building Beta is ready")
        print(f"Dashboard: {dashboard_url}")
        print(f"Control API: http://127.0.0.1:{args.control_port}")
        print("Press Ctrl+C to stop both services.\n")
        if not args.no_browser:
            webbrowser.open(dashboard_url)

        while simulator.poll() is None and dashboard.poll() is None:
            time.sleep(0.5)
        if simulator.returncode not in (None, 0):
            raise RuntimeError(f"Simulator stopped with code {simulator.returncode}")
        if dashboard.returncode not in (None, 0):
            raise RuntimeError(f"Dashboard stopped with code {dashboard.returncode}")
    except KeyboardInterrupt:
        print("\nStopping Sentinel Building Beta...")
    finally:
        terminate(dashboard)
        terminate(simulator)


if __name__ == "__main__":
    main()

