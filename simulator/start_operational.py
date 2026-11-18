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
DEFAULT_BACKEND = "http://127.0.0.1:8089"


def node_tokens(spec: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for item in spec.split(","):
        node, separator, token = item.strip().partition("=")
        if separator and node.strip() and token.strip():
            tokens[node.strip()] = token.strip()
    return tokens


def wait_for(url: str, timeout: float = 25.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"El servicio no respondió: {url}")


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def launch(
    folder: str,
    *arguments: str,
    script: str = "operational_main.py",
    env: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-u", script, *arguments],
        cwd=ROOT / folder,
        env=env,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia el simulador completo de Sentinel Building")
    parser.add_argument("--window-seconds", type=float, default=30.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--dashboard-port", type=int, default=8982)
    parser.add_argument("--bridge-1-port", type=int, default=8991)
    parser.add_argument("--bridge-2-port", type=int, default=8992)
    parser.add_argument("--brigadist-port", type=int, default=8993)
    parser.add_argument("--radio-port", type=int, default=9200)
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SENTINEL_BACKEND_URL", DEFAULT_BACKEND),
        help="URL de monolito-escucha; por defecto usa http://127.0.0.1:8089",
    )
    parser.add_argument(
        "--offline-demo", action="store_true",
        help="Inicia sin backend para probar únicamente SQLite y LoRa",
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    runtime = ROOT / "runtime" / "simulator"
    runtime.mkdir(parents=True, exist_ok=True)
    shared_env = os.environ.copy()
    shared_env.setdefault("SENTINEL_LORA_KEY", "sentinel-simulator-shared-key")
    configured_tokens = node_tokens(shared_env.get("SENTINEL_NODE_TOKENS", ""))
    configured_tokens["NODE-FLOOR-1"] = shared_env.get(
        "SENTINEL_NODE_TOKEN_FLOOR_1", configured_tokens.get("NODE-FLOOR-1", "")
    )
    configured_tokens["NODE-FLOOR-2"] = shared_env.get(
        "SENTINEL_NODE_TOKEN_FLOOR_2", configured_tokens.get("NODE-FLOOR-2", "")
    )
    backend_url = None if args.offline_demo else args.backend_url
    if backend_url:
        missing = [node for node, token in configured_tokens.items() if not token]
        if missing:
            parser.error(
                "Faltan tokens para " + ", ".join(missing)
                + ". Define SENTINEL_NODE_TOKENS o usa --offline-demo."
            )
    processes: list[subprocess.Popen[bytes]] = []

    try:
        processes.append(launch(
            "brigadist-receiver/emulator", "--host", args.host, "--web-port", str(args.brigadist_port),
            "--radio-port", str(args.radio_port),
            "--history", str(runtime / "brigadist_alerts.json"), script="main.py", env=shared_env,
        ))

        for node, port in (
            ("NODE-FLOOR-1", args.bridge_1_port),
            ("NODE-FLOOR-2", args.bridge_2_port),
        ):
            command = [
                "--node", node, "--host", args.host, "--port", str(port), "--data-dir", str(runtime),
                "--receiver-port", str(args.radio_port),
            ]
            if backend_url:
                command.extend([
                    "--backend-url", backend_url,
                    "--node-token", configured_tokens[node],
                ])
            processes.append(launch("bridge", *command, env=shared_env))

        bridge_1 = f"http://127.0.0.1:{args.bridge_1_port}"
        bridge_2 = f"http://127.0.0.1:{args.bridge_2_port}"
        wait_for(f"{bridge_1}/api/health")
        wait_for(f"{bridge_2}/api/health")

        processes.append(launch(
            "simulator", "--host", args.host, "--port", str(args.dashboard_port),
            "--window-seconds", str(args.window_seconds),
            "--bridge-1", bridge_1, "--bridge-2", bridge_2, env=shared_env,
        ))

        dashboard_url = f"http://127.0.0.1:{args.dashboard_port}/"
        brigadist_url = f"http://127.0.0.1:{args.brigadist_port}/"
        wait_for(brigadist_url)
        wait_for(f"{dashboard_url}api/state")

        print("\nSentinel Building Simulator está funcionando")
        print(f"Dashboard del simulador: {dashboard_url}")
        print(f"Receptor del brigadista: {brigadist_url}")
        print(f"Bridge Piso 1: {bridge_1}")
        print(f"Bridge Piso 2: {bridge_2}")
        print(f"Backend: {backend_url or 'desactivado para esta demostración'}")
        print("Arquitectura: 2 monolitos y 1 receptor Heltec; el bridge se despliega una vez por piso.")
        print("Presiona Ctrl+C para detener todo.\n")
        if not args.no_browser:
            webbrowser.open(dashboard_url)

        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        failed = [process.returncode for process in processes if process.poll() is not None]
        raise RuntimeError(f"Un proceso terminó inesperadamente: {failed}")
    except KeyboardInterrupt:
        print("\nDeteniendo Simulator...")
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    main()
