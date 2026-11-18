from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.negocio.simulator_service import SimulatorService


ROOT = Path(__file__).resolve().parent / "dashboard"
ASSETS = ROOT / "assets"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Handler(BaseHTTPRequestHandler):
    simulator: SimulatorService

    def _bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._bytes(status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _bridge_states(self) -> list[dict[str, Any]]:
        return [client.state() for client in self.simulator.clients.values()]

    def _state(self) -> dict[str, Any]:
        parts = self._bridge_states()
        nodes = [part["node"] for part in parts]
        sensors = [sensor for part in parts for sensor in part["sensors"]]
        logs = sorted(
            [log for part in parts for log in part["logs"]],
            key=lambda item: item.get("created_at", ""), reverse=True,
        )[:24]
        counts = {
            key: sum(int(part["counts"].get(key, 0)) for part in parts)
            for key in ("summaries", "pending", "raw_readings", "rest_sent", "lora_sent", "errors")
        }
        payloads = [part["latest_payload"] for part in parts if part["latest_payload"]]
        payloads.sort(key=lambda item: item.get("generated_at", ""), reverse=True)
        return {
            "ready": bool(parts), "updated_at": now_iso(), "nodes": nodes,
            "sensors": sensors, "logs": logs, "counts": counts,
            "error_total": counts["errors"],
            "latest_payload": payloads[0] if payloads else {},
            "latest": {part["node"]["node_id"]: part["latest_payload"] for part in parts},
            "storage": {"capacity_gb": 128, "limit_percent": 70, "raw_persisted": 0},
            "simulator_errors": dict(self.simulator.last_errors),
        }

    def _control_status(self) -> dict[str, Any]:
        parts = [client.status() for client in self.simulator.clients.values()]
        bridges, lora = {}, {}
        for part in parts:
            bridges.update(part["bridges"])
            lora.update(part["lora"])
        return {
            "network_up": all(part["network_up"] for part in parts),
            "bridges": bridges, "lora": lora,
        }

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/state":
                self._json(200, self._state())
                return
            if path == "/api/control/status":
                self._json(200, self._control_status())
                return
            if path in {"/", "/index.html"}:
                self._bytes(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
                return
            if path.startswith("/assets/"):
                asset = (ASSETS / path.removeprefix("/assets/")).resolve()
                if ASSETS.resolve() in asset.parents and asset.is_file():
                    content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                    if asset.suffix.lower() == ".glb":
                        content_type = "model/gltf-binary"
                    self._bytes(200, content_type, asset.read_bytes())
                    return
            self._json(404, {"detail": "Not found"})
        except (OSError, RuntimeError) as exc:
            self._json(503, {"ok": False, "detail": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/control":
            self._json(404, {"detail": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if body.get("action") == "anomaly":
                result = self.simulator.anomaly(
                    body["target"], body["sensor"], bool(body["value"])
                )
                self._json(200, {"ok": True, **result})
            else:
                results = self.simulator.control(body)
                self._json(200, {
                    "ok": True,
                    "pending_replayed": sum(item.get("pending_replayed", 0) for item in results),
                })
        except (KeyError, TypeError, ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            self._json(400, {"ok": False, "detail": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"simulator-dashboard | {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Simulator Monolith")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8982)
    parser.add_argument("--window-seconds", type=float, default=30.0)
    parser.add_argument("--bridge-1", default="http://127.0.0.1:8991")
    parser.add_argument("--bridge-2", default="http://127.0.0.1:8992")
    args = parser.parse_args()
    Handler.simulator = SimulatorService(
        {"NODE-FLOOR-1": args.bridge_1, "NODE-FLOOR-2": args.bridge_2},
        args.window_seconds,
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Simulator Monolith: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Handler.simulator.close()
        server.server_close()


if __name__ == "__main__":
    main()
