from __future__ import annotations

import argparse
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.core.catalog import NODES
from app.negocio.bridge_service import BridgeService


def read_evidence(service: BridgeService) -> dict:
    path = service.store.path
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT generated_at,payload_json,delivery_status FROM summaries "
            "ORDER BY generated_at DESC LIMIT 40"
        ).fetchall()
        payloads = [json.loads(row["payload_json"]) for row in rows]
        logs = [dict(row) for row in con.execute(
            "SELECT created_at,message_uid,node_code,transport,result "
            "FROM sync_log ORDER BY id DESC LIMIT 24"
        ).fetchall()]
        counts = {
            "summaries": con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0],
            "pending": con.execute(
                "SELECT COUNT(*) FROM summaries WHERE delivery_status IN ('pending','pending_backend')"
            ).fetchone()[0],
            "raw_readings": con.execute(
                "SELECT COALESCE(SUM(CAST(json_extract(payload_json,'$.window.sample_count') AS INTEGER)),0) FROM summaries"
            ).fetchone()[0],
            "rest_sent": con.execute(
                "SELECT COUNT(*) FROM sync_log WHERE transport='rest' AND result='accepted'"
            ).fetchone()[0],
            "lora_sent": con.execute(
                "SELECT COUNT(*) FROM sync_log WHERE transport='lora' AND result='accepted'"
            ).fetchone()[0],
            "errors": con.execute(
                "SELECT COUNT(*) FROM sync_log WHERE result IN ('retry','error','failed')"
            ).fetchone()[0],
        }
    finally:
        con.close()

    latest = payloads[0] if payloads else {}
    bridge = (latest.get("bridges") or [{}])[0]
    sensors = [
        {**sensor, "node": service.node_code, "floor": NODES[service.node_code]["floor"]}
        for sensor in bridge.get("sensors", [])
    ]
    return {
        "node": {
            "node_id": service.node_code,
            "floor": NODES[service.node_code]["floor"],
            "summaries": counts["summaries"], "pending": counts["pending"],
            "status": "online" if service.online else "offline",
            "last_seen": latest.get("generated_at"),
        },
        "latest_payload": latest,
        "sensors": sensors,
        "logs": logs,
        "counts": counts,
    }


class Handler(BaseHTTPRequestHandler):
    service: BridgeService

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"ok": True, "node": self.service.node_code})
        elif path == "/api/control/status":
            status = self.service.status()
            self._json(200, {
                "network_up": status["network_up"],
                "bridges": {self.service.node_code: status},
                "lora": {self.service.node_code: status["lora_up"]},
            })
        elif path == "/api/state":
            self._json(200, read_evidence(self.service))
        else:
            self._json(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if path == "/api/ingest":
                aggregate = self.service.ingest(body["events"], float(body["window_seconds"]))
                self._json(202, {
                    "ok": True, "message_uid": aggregate["message_uid"],
                    "priority": aggregate["priority"], "delivery_policy": aggregate["delivery_policy"],
                    "last_sync": self.service.last_sync,
                })
                return
            if path == "/api/control":
                target = body.get("target")
                if target and target != self.service.node_code:
                    self._json(409, {"detail": "Command targets another bridge"})
                    return
                replayed = self.service.command(body["action"], bool(body["value"]))
                self._json(200, {"ok": True, "pending_replayed": replayed})
                return
            self._json(404, {"detail": "Not found"})
        except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            self._json(400, {"ok": False, "detail": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"bridge-api | {self.service.node_code} | {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Bridge Monolith")
    parser.add_argument("--node", choices=tuple(NODES), required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--node-token", default="")
    parser.add_argument("--receiver-host", default="127.0.0.1")
    parser.add_argument("--receiver-port", type=int, default=9200)
    parser.add_argument("--shared-key", default=os.getenv("SENTINEL_LORA_KEY", "sentinel-simulator-shared-key"))
    parser.add_argument("--lora-loss-rate", type=float, default=0.0)
    args = parser.parse_args()

    Handler.service = BridgeService(
        args.node, Path(args.data_dir), args.backend_url, args.node_token,
        args.receiver_host, args.receiver_port, args.shared_key.encode("utf-8"),
        loss_rate=args.lora_loss_rate,
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Bridge Monolith {args.node}: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        Handler.service.close()


if __name__ == "__main__":
    main()
