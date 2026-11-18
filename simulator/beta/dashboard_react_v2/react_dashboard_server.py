from __future__ import annotations

import argparse
import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
ASSETS = PROJECT_ROOT / "dashboard" / "assets"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_db(path: Path) -> dict:
    if not path.exists():
        return {"ready": False, "payloads": [], "pending": 0, "summaries": 0, "logs": []}
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        summaries = con.execute(
            "SELECT message_uid,node_code,generated_at,payload_json,delivery_status,attempts,response "
            "FROM summaries ORDER BY generated_at DESC LIMIT 40"
        ).fetchall()
        pending = con.execute(
            "SELECT COUNT(*) FROM summaries "
            "WHERE delivery_status IN ('pending', 'pending_backend')"
        ).fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
        raw_readings = con.execute(
            "SELECT COALESCE(SUM(CAST(json_extract(payload_json, '$.window.sample_count') AS INTEGER)), 0) FROM summaries"
        ).fetchone()[0]
        rest_sent = con.execute(
            "SELECT COUNT(*) FROM sync_log WHERE transport='rest' AND result IN ('accepted','sent','202')"
        ).fetchone()[0]
        lora_sent = con.execute(
            "SELECT COUNT(*) FROM sync_log WHERE transport='lora' AND result IN ('accepted','sent')"
        ).fetchone()[0]
        error_total = con.execute(
            "SELECT COUNT(*) FROM sync_log WHERE result IN ('retry','error','failed')"
        ).fetchone()[0]
        response_counts = [dict(row) for row in con.execute(
            "SELECT COALESCE(response, 'no response') AS response, COUNT(*) AS total "
            "FROM summaries GROUP BY response ORDER BY total DESC"
        ).fetchall()]
        logs = con.execute(
            "SELECT created_at,message_uid,node_code,transport,result FROM sync_log ORDER BY id DESC LIMIT 20"
        ).fetchall()
        payloads = []
        for row in summaries:
            item = dict(row)
            try:
                item["payload"] = json.loads(item.pop("payload_json"))
            except json.JSONDecodeError:
                item["payload"] = {}
            payloads.append(item)
        return {
            "ready": True,
            "payloads": payloads,
            "latest": payloads[0] if payloads else None,
            "pending": pending,
            "summaries": total,
            "raw_readings": int(raw_readings or 0),
            "rest_sent": int(rest_sent or 0),
            "lora_sent": int(lora_sent or 0),
            "error_total": int(error_total or 0),
            "response_counts": response_counts,
            "logs": [dict(row) for row in logs],
        }
    finally:
        con.close()


def read_shared_sensors(mock_backend_url: str) -> tuple[list[dict] | None, str | None]:
    url = f"{mock_backend_url.rstrip('/')}/api/v1/sensors/latest"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict) or not isinstance(payload.get("sensors"), list):
        return None, "Mock backend returned an invalid latest-sensors response"
    return payload["sensors"], None


class DashboardData:
    def __init__(self, data_dir: Path, mock_backend_url: str) -> None:
        self.data_dir = data_dir
        self.mock_backend_url = mock_backend_url

    def read(self) -> dict:
        bridges = [read_db(self.data_dir / "node-floor-1_summary.db"), read_db(self.data_dir / "node-floor-2_summary.db")]
        latest_by_node = {node: next((item for item in db["payloads"] if item["node_code"] == node), None)
                          for node, db in zip(("NODE-FLOOR-1", "NODE-FLOOR-2"), bridges)}
        payloads = [item["payload"] for item in latest_by_node.values() if item]
        sensors = []
        for payload in payloads:
            for bridge in payload.get("bridges", []):
                for sensor in bridge.get("sensors", []):
                    sensors.append({
                        **sensor,
                        "node": bridge.get("node_code"),
                        "floor": bridge.get("floor"),
                        "source": "beta",
                    })
        shared_sensors, shared_backend_error = read_shared_sensors(self.mock_backend_url)
        if shared_sensors is not None:
            sensors = shared_sensors
        logs = []
        for db in bridges:
            logs.extend(db["logs"])
        logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        pending = sum(db["pending"] for db in bridges)
        summaries = sum(db["summaries"] for db in bridges)
        raw_readings = sum(db["raw_readings"] for db in bridges)
        rest_sent = sum(db["rest_sent"] for db in bridges)
        lora_sent = sum(db["lora_sent"] for db in bridges)
        error_total = sum(db["error_total"] for db in bridges)
        response_counts = {}
        for db in bridges:
            for item in db["response_counts"]:
                response_counts[item["response"]] = response_counts.get(item["response"], 0) + item["total"]
        last_generated = max((item["generated_at"] for item in latest_by_node.values() if item), default=None)
        return {
            "ready": any(db["ready"] for db in bridges),
            "updated_at": now_iso(),
            "data_dir": str(self.data_dir),
            "bridge": {"status": "online" if payloads else "waiting", "last_seen": last_generated},
            "counts": {"summaries": summaries, "pending": pending, "raw_readings": raw_readings, "rest_sent": rest_sent, "lora_sent": lora_sent, "errors": error_total},
            "nodes": [
                {"node_id": node, "floor": index, "summaries": db["summaries"], "pending": db["pending"],
                 "status": "online" if db["ready"] else "waiting", "last_seen": (db["latest"] or {}).get("generated_at")}
                for index, (node, db) in enumerate(zip(("NODE-FLOOR-1", "NODE-FLOOR-2"), bridges), 1)
            ],
            "latest_payload": payloads[0] if payloads else {},
            "latest": latest_by_node,
            "sensors": sensors,
            "shared_backend": {
                "connected": shared_sensors is not None,
                "url": self.mock_backend_url,
                "detail": shared_backend_error,
            },
            "logs": logs[:24],
            "response_counts": response_counts,
            "error_total": error_total,
            "storage": {"capacity_gb": 128, "limit_percent": 70, "raw_persisted": 0},
        }


class Handler(BaseHTTPRequestHandler):
    data: DashboardData
    control_url: str

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: dict) -> None:
        self.send_bytes(status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/state":
            self.send_json(200, self.data.read())
            return
        if path == "/api/control/status":
            try:
                with urllib.request.urlopen(f"{self.control_url}/api/control/status", timeout=2) as response:
                    self.send_bytes(response.status, "application/json; charset=utf-8", response.read())
            except OSError as exc:
                self.send_json(503, {"ok": False, "detail": str(exc)})
            return
        if path in {"/", "/index.html"}:
            self.send_bytes(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
            return
        if path.startswith("/assets/"):
            asset = (ASSETS / path.removeprefix("/assets/")).resolve()
            assets_root = ASSETS.resolve()
            if assets_root in asset.parents and asset.is_file():
                content_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml"}.get(asset.suffix.lower(), "application/octet-stream")
                self.send_bytes(200, content_type, asset.read_bytes())
                return
        self.send_json(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/control":
            self.send_json(404, {"detail": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(size)
            request = urllib.request.Request(
                f"{self.control_url}/api/control", data=body,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                self.send_bytes(response.status, "application/json; charset=utf-8", response.read())
        except urllib.error.HTTPError as exc:
            self.send_json(exc.code, {"ok": False, "detail": exc.read().decode("utf-8", errors="replace")})
        except OSError as exc:
            self.send_json(503, {"ok": False, "detail": f"Simulator control unavailable: {exc}"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"react-dashboard | {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="React dashboard for Sentinel simulation v2")
    parser.add_argument("--data-dir", default="data_simulation_v2")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8782)
    parser.add_argument("--control-url", default="http://127.0.0.1:8792")
    parser.add_argument(
        "--mock-backend-url",
        default=os.getenv("SENTINEL_MOCK_BACKEND_URL") or "http://127.0.0.1:8000",
    )
    args = parser.parse_args()
    Handler.data = DashboardData(Path(args.data_dir), args.mock_backend_url)
    Handler.control_url = args.control_url.rstrip("/")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"React dashboard ready | http://{args.host}:{args.port} | data={args.data_dir} | control={Handler.control_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

