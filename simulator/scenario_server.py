"""Servidor del panel de escenarios para Sentinel Building.

El panel administra el proceso del simulador y activa anomalías mediante
comandos por stdin. No modifica el contrato JSON ni los archivos existentes.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
PANEL_DIR = Path(__file__).resolve().parent
HTML_PATH = PANEL_DIR / "scenario_index.html"

ALLOWED_NODES = ("NODE-FLOOR-1", "NODE-FLOOR-2")

SCENARIOS: dict[str, dict[str, Any]] = {
    "fire": {
        "label": "Fire",
        "sensors": ("grideye", "bme688"),
        "default_nodes": ALLOWED_NODES,
    },
    "earthquake": {
        "label": "Earthquake",
        "sensors": ("adxl355",),
        "default_nodes": ALLOWED_NODES,
    },
    "power_failure": {
        "label": "Power failure",
        "sensors": ("ina219",),
        "default_nodes": (),
    },
}

ALL_NODE_SENSORS = tuple(
    (node, sensor)
    for node in ALLOWED_NODES
    for sensor in ("grideye", "bme688", "adxl355", "ina219")
)


def utc_now() -> str:
    """Devuelve la hora UTC en un formato legible para el panel."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_from_root(value: str) -> Path:
    """Interpreta rutas relativas respecto a la raíz del proyecto."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def bridge_is_listening(host: str, port: int, timeout: float = 0.5) -> bool:
    """Comprueba si hay un servicio escuchando en el puerto del bridge."""
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def normalize_nodes(value: Any) -> list[str]:
    """Valida y normaliza la lista de nodos recibida por la API."""
    if not isinstance(value, list):
        raise ValueError("'nodes' debe ser una lista")

    nodes: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("Cada nodo debe ser una cadena de texto")
        node = item.strip()
        if node not in ALLOWED_NODES:
            raise ValueError(f"Nodo no permitido: {node}")
        if node not in nodes:
            nodes.append(node)
    return nodes


def read_bridge_metrics(data_dir: str) -> dict[str, Any]:
    """Lee las métricas de SQLite en modo de solo lectura."""
    db_path = resolve_from_root(data_dir) / "bridge_local.db"
    empty = {
        "ready": False,
        "message": "Bridge database not found",
        "raw_readings": 0,
        "aggregates_total": 0,
        "sent_rest": 0,
        "pending": 0,
        "last_priority": None,
        "last_message_uid": None,
    }
    if not db_path.is_file():
        return empty

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            f"{db_path.as_uri()}?mode=ro",
            uri=True,
            timeout=1.0,
        )
        raw_total = connection.execute(
            "SELECT COUNT(*) FROM raw_reading"
        ).fetchone()[0]
        aggregate_total = connection.execute(
            "SELECT COUNT(*) FROM aggregate_outbox"
        ).fetchone()[0]
        rest_sent = connection.execute(
            "SELECT COUNT(*) FROM aggregate_outbox WHERE status='sent_rest'"
        ).fetchone()[0]
        pending = connection.execute(
            "SELECT COUNT(*) FROM aggregate_outbox WHERE status='pending'"
        ).fetchone()[0]
        latest = connection.execute(
            """
            SELECT message_uid, payload_json
            FROM aggregate_outbox
            ORDER BY generated_at DESC
            LIMIT 1
            """
        ).fetchone()

        last_priority = None
        last_message_uid = None
        if latest:
            last_message_uid = latest[0]
            payload = json.loads(latest[1])
            last_priority = payload.get("priority")

        return {
            "ready": True,
            "message": "Bridge database available",
            "raw_readings": int(raw_total),
            "aggregates_total": int(aggregate_total),
            "sent_rest": int(rest_sent),
            "pending": int(pending),
            "last_priority": last_priority,
            "last_message_uid": last_message_uid,
        }
    except (sqlite3.Error, json.JSONDecodeError, OSError, ValueError):
        return {
            **empty,
            "message": "Bridge database is not ready or has an invalid schema",
        }
    finally:
        if connection is not None:
            connection.close()


class ScenarioController:
    """Estado compartido y operaciones sobre el simulador."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.process: subprocess.Popen[str] | None = None
        self.reader_thread: threading.Thread | None = None
        self.simulator_log: deque[str] = deque(maxlen=100)
        self.event_log: deque[dict[str, str]] = deque(maxlen=200)
        self.active_scenario: dict[str, Any] | None = None
        self.scenario_token = 0
        self.started_by_panel = False
        self.last_process_exit: str | None = None

    def _record_event(self, action: str, detail: str) -> None:
        self.event_log.append({
            "timestamp": utc_now(),
            "action": action,
            "detail": detail,
        })

    def _record_output(self, line: str) -> None:
        line = line.rstrip("\r\n")
        if not line:
            return
        with self.lock:
            self.simulator_log.append(f"[{utc_now()}] {line}")

    def _process_is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _send_command(self, command: str) -> bool:
        """Escribe una línea al stdin sin cerrar la tubería."""
        process = self.process
        if process is None or process.poll() is not None or process.stdin is None:
            return False
        try:
            process.stdin.write(command + "\n")
            process.stdin.flush()
            self._record_event("Command", command)
            return True
        except (BrokenPipeError, OSError, ValueError):
            self._record_event("Error", f"Could not send command: {command}")
            return False

    def _clear_pairs(self, pairs: tuple[tuple[str, str], ...] | list[tuple[str, str]]) -> None:
        for node, sensor in pairs:
            self._send_command(f"clear {node} {sensor}")

    def start_simulator(
        self,
        bridge_url: str,
        interval_s: float,
        simulator_data_dir: str,
    ) -> dict[str, Any]:
        with self.lock:
            if self._process_is_running():
                return {"ok": False, "error": "The simulator is already running."}

            script = ROOT / "mqtt_sensor_simulator.py"
            if not script.is_file():
                return {
                    "ok": False,
                    "error": f"Simulator script not found: {script}",
                }

            command = [
                sys.executable,
                "-u",
                str(script),
                "--bridge-url",
                bridge_url,
                "--interval",
                str(interval_s),
                "--data-dir",
                simulator_data_dir,
            ]

            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(ROOT),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                return {"ok": False, "error": f"Could not start simulator: {exc}"}

            self.process = process
            self.started_by_panel = True
            self.last_process_exit = None
            self._record_event("Simulator", "Simulator started by the scenario panel.")
            self.reader_thread = threading.Thread(
                target=self._read_process_output,
                args=(process,),
                name="scenario-simulator-output",
                daemon=True,
            )
            self.reader_thread.start()

        return {"ok": True, "message": "Simulator started."}

    def _read_process_output(self, process: subprocess.Popen[str]) -> None:
        """Guarda la salida del proceso en un buffer circular."""
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    self._record_output(line)
        except (OSError, ValueError) as exc:
            self._record_output(f"Output reader error: {exc}")
        finally:
            return_code = process.poll()
            with self.lock:
                if self.process is process and return_code is not None:
                    self.last_process_exit = (
                        f"Simulator stopped with exit code {return_code}."
                    )
                    self._record_event("Simulator", self.last_process_exit)
                    self.process = None
                    self.started_by_panel = False
                    self._invalidate_scenario()

    def _invalidate_scenario(self) -> None:
        self.scenario_token += 1
        self.active_scenario = None

    def start_scenario(
        self,
        scenario_name: str,
        nodes: list[str],
        duration_s: int | None,
    ) -> dict[str, Any]:
        with self.lock:
            if not self._process_is_running():
                return {
                    "ok": False,
                    "error": "Start the simulator before activating a scenario.",
                }

            if self.active_scenario is not None:
                self._stop_active_scenario_locked()

            self.scenario_token += 1
            token = self.scenario_token
            scenario = SCENARIOS[scenario_name]
            sensors = tuple(scenario["sensors"])
            pairs = [(node, sensor) for node in nodes for sensor in sensors]

            self.active_scenario = {
                "name": scenario_name,
                "label": scenario["label"],
                "nodes": list(nodes),
                "sensors": list(sensors),
                "pairs": pairs,
                "duration_s": duration_s,
                "started_at": utc_now(),
                "started_monotonic": time.monotonic(),
                "token": token,
            }
            self._record_event(
                "Scenario",
                f"Activated {scenario_name}; nodes={', '.join(nodes)}; "
                f"duration={'manual' if duration_s is None else str(duration_s) + ' s'}",
            )

        worker = threading.Thread(
            target=self._run_scenario,
            args=(scenario_name, pairs, duration_s, token),
            name=f"scenario-{scenario_name}",
            daemon=True,
        )
        worker.start()
        return {"ok": True, "message": "Scenario activated."}

    def _run_scenario(
        self,
        scenario_name: str,
        pairs: list[tuple[str, str]],
        duration_s: int | None,
        token: int,
    ) -> None:
        """Envía los comandos del escenario y administra su duración."""
        for index, (node, sensor) in enumerate(pairs):
            with self.lock:
                if (
                    self.active_scenario is None
                    or self.active_scenario.get("token") != token
                    or not self._process_is_running()
                ):
                    return
                self._send_command(f"anomaly {node} {sensor}")

            if index < len(pairs) - 1:
                time.sleep(0.3)

        if duration_s is None:
            return

        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            with self.lock:
                if (
                    self.active_scenario is None
                    or self.active_scenario.get("token") != token
                ):
                    return
            time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))

        with self.lock:
            active = self.active_scenario
            if active is None or active.get("token") != token:
                return
            self._clear_pairs(pairs)
            self.active_scenario = None
            self.scenario_token += 1
            self._record_event(
                "Scenario",
                f"Duration complete; cleared {scenario_name}.",
            )

    def _stop_active_scenario_locked(self) -> None:
        """Detiene y limpia únicamente los sensores del escenario activo."""
        scenario = self.active_scenario
        self.scenario_token += 1
        self.active_scenario = None
        if scenario is None:
            return
        pairs = scenario.get("pairs", [])
        self._clear_pairs(pairs)
        self._record_event(
            "Scenario",
            f"Stopped and cleared {scenario.get('name', 'active scenario')}.",
        )

    def stop_scenario(self) -> dict[str, Any]:
        with self.lock:
            if self.active_scenario is not None:
                self._stop_active_scenario_locked()
            else:
                self.scenario_token += 1
            self._clear_pairs(list(ALL_NODE_SENSORS))
            self._record_event("Scenario", "All scenario sensor combinations cleared.")
        return {"ok": True, "message": "All scenarios stopped; sensors cleared."}

    def stop_simulator(self) -> dict[str, Any]:
        with self.lock:
            process = self.process
            if process is None:
                return {"ok": False, "error": "The simulator is not running."}

            if self.active_scenario is not None:
                self._stop_active_scenario_locked()

            # Detener todos los sensores antes de solicitar el cierre normal.
            self._clear_pairs(list(ALL_NODE_SENSORS))
            self._send_command("quit")

        forced = False
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            forced = True
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        with self.lock:
            if self.process is process:
                self.process = None
            self.started_by_panel = False
            self._invalidate_scenario()
            self._record_event(
                "Simulator",
                "Simulator stopped." + (" Forced termination was required." if forced else ""),
            )

        return {
            "ok": True,
            "message": "Simulator stopped.",
            "forced": forced,
        }

    def status(self) -> dict[str, Any]:
        with self.lock:
            process_running = self._process_is_running()
            scenario = self.active_scenario
            elapsed_s: float | None = None
            countdown_s: int | None = None

            if scenario is not None:
                elapsed = time.monotonic() - scenario["started_monotonic"]
                elapsed_s = round(max(0.0, elapsed), 1)
                duration_s = scenario["duration_s"]
                if duration_s is not None:
                    countdown_s = max(0, int(duration_s - elapsed))

            scenario_info = None
            if scenario is not None:
                scenario_info = {
                    "name": scenario["name"],
                    "label": scenario["label"],
                    "nodes": list(scenario["nodes"]),
                    "sensors": list(scenario["sensors"]),
                    "duration_s": scenario["duration_s"],
                    "started_at": scenario["started_at"],
                    "elapsed_s": elapsed_s,
                    "countdown_s": countdown_s,
                }

            return {
                "simulator_running": process_running,
                "started_by_panel": self.started_by_panel,
                "simulator_pid": self.process.pid if process_running and self.process else None,
                "scenario": scenario_info,
                "log": list(self.simulator_log),
                "events": list(self.event_log),
                "last_process_exit": self.last_process_exit,
            }


class ScenarioRequestHandler(BaseHTTPRequestHandler):
    server: "ScenarioHTTPServer"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            try:
                body = HTML_PATH.read_bytes()
            except OSError:
                self._send_json(500, {"detail": "Scenario interface file is unavailable."})
                return
            self._send_bytes(200, "text/html; charset=utf-8", body)
            return

        if path == "/api/status":
            status = self.server.controller.status()
            bridge = read_bridge_metrics(self.server.bridge_data_dir)
            bridge_active = bridge_is_listening("127.0.0.1", self.server.bridge_port)
            manual_warning = ""
            if bridge_active and not status["started_by_panel"]:
                manual_warning = (
                    "The bridge is active but this panel did not start the simulator. "
                    "If a simulator is running in another terminal, close it before "
                    "starting a simulator from this panel."
                )
            payload = {
                "status": status,
                "bridge": bridge,
                "bridge_active": bridge_active,
                "warning": manual_warning,
            }
            self._send_json(200, payload)
            return

        self._send_json(404, {"detail": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._send_json(400, {"detail": str(exc)})
            return

        if path == "/api/simulator/start":
            result = self.server.controller.start_simulator(
                self.server.bridge_url,
                self.server.interval_s,
                self.server.simulator_data_dir,
            )
            self._send_json(200 if result["ok"] else 400, result)
            return

        if path == "/api/simulator/stop":
            result = self.server.controller.stop_simulator()
            self._send_json(200 if result["ok"] else 400, result)
            return

        if path == "/api/scenario/start":
            try:
                result = self._start_scenario(payload)
            except ValueError as exc:
                self._send_json(400, {"detail": str(exc)})
                return
            self._send_json(200 if result["ok"] else 400, result)
            return

        if path == "/api/scenario/stop":
            result = self.server.controller.stop_scenario()
            self._send_json(200 if result["ok"] else 400, result)
            return

        self._send_json(404, {"detail": "Not found."})

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header.") from exc

        if length < 0 or length > 64 * 1024:
            raise ValueError("Request body must be no larger than 64 KiB.")
        if length == 0:
            return {}

        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must contain valid UTF-8 JSON.") from exc

        if not isinstance(value, dict):
            raise ValueError("Request JSON must be an object.")
        return value

    def _start_scenario(self, payload: dict[str, Any]) -> dict[str, Any]:
        scenario_name = payload.get("scenario")
        if not isinstance(scenario_name, str):
            raise ValueError("'scenario' must be a string.")
        scenario_name = scenario_name.strip().lower()
        if scenario_name not in SCENARIOS:
            raise ValueError("Unknown scenario. Use fire, earthquake, or power_failure.")

        nodes = normalize_nodes(payload.get("nodes", []))
        if scenario_name == "power_failure":
            if len(nodes) != 1:
                raise ValueError("Power failure requires exactly one selected node.")
        elif not nodes:
            nodes = list(SCENARIOS[scenario_name]["default_nodes"])

        duration = payload.get("duration_s")
        if duration is not None:
            if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                raise ValueError("'duration_s' must be a positive integer or null.")

        return self.server.controller.start_scenario(
            scenario_name,
            nodes,
            duration,
        )

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", body)

    def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"scenario-panel | {fmt % args}")


class ScenarioHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        host: str,
        port: int,
        *,
        controller: ScenarioController,
        bridge_url: str,
        interval_s: float,
        simulator_data_dir: str,
        bridge_data_dir: str,
        bridge_port: int,
    ) -> None:
        super().__init__((host, port), ScenarioRequestHandler)
        self.controller = controller
        self.bridge_url = bridge_url
        self.interval_s = interval_s
        self.simulator_data_dir = simulator_data_dir
        self.bridge_data_dir = bridge_data_dir
        self.bridge_port = bridge_port


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Panel de simulación de escenarios de Sentinel Building"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--bridge-url", default="http://127.0.0.1:8766")
    parser.add_argument("--bridge-port", type=int, default=8766)
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--simulator-data-dir", default="data_sensor_simulator")
    parser.add_argument("--data-dir", default="data_bridge")
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535")
    if not 1 <= args.bridge_port <= 65535:
        parser.error("--bridge-port debe estar entre 1 y 65535")
    if args.interval <= 0:
        parser.error("--interval debe ser positivo")
    if not args.bridge_url.startswith(("http://", "https://")):
        parser.error("--bridge-url debe ser una URL HTTP o HTTPS")

    controller = ScenarioController()
    try:
        server = ScenarioHTTPServer(
            args.host,
            args.port,
            controller=controller,
            bridge_url=args.bridge_url,
            interval_s=args.interval,
            simulator_data_dir=args.simulator_data_dir,
            bridge_data_dir=args.data_dir,
            bridge_port=args.bridge_port,
        )
    except OSError as exc:
        raise SystemExit(
            f"No se pudo iniciar el panel en {args.host}:{args.port}: {exc}"
        ) from exc

    print(f"Scenario panel: http://{args.host}:{args.port}")
    print(f"Simulator bridge URL: {args.bridge_url}")
    print(f"Bridge database directory: {resolve_from_root(args.data_dir)}")
    if bridge_is_listening("127.0.0.1", args.bridge_port):
        print(
            "Advertencia: el bridge está activo. Si el simulador fue iniciado "
            "manualmente en otra terminal, ciérralo antes de iniciarlo desde el panel."
        )

    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nCerrando el panel...")
    finally:
        # Al cerrar el panel se limpian anomalías y se solicita el cierre normal.
        controller.stop_scenario()
        if controller.status()["simulator_running"]:
            controller.stop_simulator()
        server.server_close()
        print("Panel detenido.")

if __name__ == "__main__":
    main()