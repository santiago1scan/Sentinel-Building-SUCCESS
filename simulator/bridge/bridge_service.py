"""Bridge Sentinel independiente.

El bridge recibe lecturas internas del simulador, guarda las lecturas originales
en SQLite, construye el JSON estándar y lo entrega al backend central. REST se
usa para datos nuevos; MQTT se usa para recuperar la cola pendiente; LoRa solo
envía un resumen al brigadista cuando no hay conectividad.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telemetry_standard import aggregate_readings  # noqa: E402
from virtual_lora import VirtualRadioChannel  # noqa: E402

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # Permite ejecutar el bridge sin MQTT durante pruebas.
    mqtt = None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_reading (
    event_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_reading_time
    ON raw_reading(generated_at);
CREATE TABLE IF NOT EXISTS aggregate_outbox (
    message_uid TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    sent_at TEXT,
    response TEXT
);
CREATE TABLE IF NOT EXISTS bridge_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT NOT NULL,
    level TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


class BridgeStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA synchronous=FULL")
        self.con.execute("PRAGMA busy_timeout=5000")
        self.con.executescript(SCHEMA)
        self.con.commit()
        self.lock = threading.Lock()

    def log(self, level: str, detail: str) -> None:
        with self.lock:
            self.con.execute(
                "INSERT INTO bridge_log(logged_at, level, detail) VALUES (?, ?, ?)",
                (now_utc(), level, detail),
            )
            self.con.commit()

    def save_readings(self, readings: list[dict[str, Any]]) -> int:
        inserted = 0
        with self.lock:
            for reading in readings:
                cursor = self.con.execute(
                    """INSERT OR IGNORE INTO raw_reading
                    (event_id, node_id, sensor_id, sensor_type, generated_at,
                     payload_json, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        reading["event_id"], reading["node_id"],
                        reading["sensor_id"], reading["sensor_type"],
                        reading["generated_at"],
                        json.dumps(reading, ensure_ascii=False), now_utc(),
                    ),
                )
                inserted += int(cursor.rowcount == 1)
            self.con.commit()
        return inserted

    def save_aggregate(self, aggregate: dict[str, Any]) -> None:
        with self.lock:
            self.con.execute(
                """INSERT OR IGNORE INTO aggregate_outbox
                (message_uid, generated_at, payload_json)
                VALUES (?, ?, ?)""",
                (
                    aggregate["message_uid"], aggregate["generated_at"],
                    json.dumps(aggregate, ensure_ascii=False),
                ),
            )
            self.con.commit()

    def pending(self, limit: int = 50) -> list[tuple[str, str, int]]:
        with self.lock:
            return self.con.execute(
                """SELECT message_uid, payload_json, attempts
                FROM aggregate_outbox WHERE status='pending'
                ORDER BY generated_at LIMIT ?""", (limit,)
            ).fetchall()

    def mark_sent(self, uid: str, status: str, response: str) -> None:
        with self.lock:
            self.con.execute(
                """UPDATE aggregate_outbox
                SET status=?, attempts=attempts+1, last_attempt_at=?,
                    sent_at=?, response=? WHERE message_uid=?""",
                (status, now_utc(), now_utc(), response, uid),
            )
            self.con.commit()

    def mark_attempt(self, uid: str, response: str) -> None:
        with self.lock:
            self.con.execute(
                """UPDATE aggregate_outbox SET attempts=attempts+1,
                last_attempt_at=?, response=? WHERE message_uid=?""",
                (now_utc(), response, uid),
            )
            self.con.commit()

    def counts(self) -> dict[str, int]:
        with self.lock:
            raw = self.con.execute("SELECT COUNT(*) FROM raw_reading").fetchone()[0]
            pending = self.con.execute(
                "SELECT COUNT(*) FROM aggregate_outbox WHERE status='pending'"
            ).fetchone()[0]
            sent = self.con.execute(
                "SELECT COUNT(*) FROM aggregate_outbox WHERE status <> 'pending'"
            ).fetchone()[0]
        return {"raw_readings": raw, "pending": pending, "sent": sent}

    def close(self) -> None:
        self.con.close()


class BridgeRuntime:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.store = BridgeStore(Path(args.data_dir) / "bridge_local.db")
        self.sequence = 0
        self.mqtt_client: Any = None
        self.mqtt_enabled = False
        self.lora = VirtualRadioChannel(
            name="lora", loss_rate=args.lora_loss_rate,
            min_delay_ms=args.lora_min_delay_ms,
            max_delay_ms=args.lora_max_delay_ms,
            max_payload_bytes=args.lora_max_payload_bytes,
            seed=args.lora_seed,
        )
        self._connect_mqtt()

    def _connect_mqtt(self) -> None:
        if mqtt is None or not self.args.mqtt_host:
            return
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"sentinel-bridge-{self.args.building_code.lower()}",
            )
            username = self.args.mqtt_username or os.getenv("SENTINEL_MQTT_USERNAME")
            password = self.args.mqtt_password or os.getenv("SENTINEL_MQTT_PASSWORD")
            if username is not None:
                client.username_pw_set(username, password or "")
            if self.args.mqtt_tls:
                client.tls_set(ca_certs=self.args.mqtt_ca_file,
                               cert_reqs=ssl.CERT_REQUIRED)
            client.reconnect_delay_set(min_delay=1, max_delay=15)
            client.connect(self.args.mqtt_host, self.args.mqtt_port, keepalive=30)
            client.loop_start()
            self.mqtt_client = client
            self.mqtt_enabled = True
            self.store.log("INFO", "MQTT conectado")
        except (OSError, ssl.SSLError) as exc:
            self.store.log("WARN", f"MQTT no disponible: {exc}")

    def _send_rest(self, uid: str, payload: dict[str, Any]) -> bool:
        if not self.args.api_url:
            return False
        outgoing = dict(payload)
        outgoing["delivery_status"] = "realtime"
        outgoing["transport"] = "rest"
        outgoing["sent_at"] = now_utc()
        path = "/api/v1/events/emergency" if outgoing["priority"] != "normal" else "/api/v1/telemetry/realtime"
        headers = {"Content-Type": "application/json"}
        if self.args.api_token:
            headers["Authorization"] = f"Bearer {self.args.api_token}"
        request = urllib.request.Request(
            self.args.api_url.rstrip("/") + path,
            data=json.dumps(outgoing, ensure_ascii=False).encode("utf-8"),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.args.api_timeout) as response:
                body = response.read().decode("utf-8")
                if 200 <= response.status < 300:
                    self.store.mark_sent(uid, "sent_rest", body)
                    return True
                self.store.mark_attempt(uid, f"HTTP {response.status}: {body}")
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            self.store.mark_attempt(uid, str(exc))
        return False

    def _send_mqtt_pending(self) -> int:
        if not self.mqtt_enabled or self.mqtt_client is None or not self.mqtt_client.is_connected():
            return 0
        sent = 0
        topic = f"sentinel/v1/{self.args.building_code}/telemetry/aggregate"
        for uid, encoded, attempts in self.store.pending():
            payload = json.loads(encoded)
            payload["delivery_status"] = "catch_up" if attempts else "realtime"
            payload["transport"] = "mqtt"
            payload["sent_at"] = now_utc()
            result = self.mqtt_client.publish(
                topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=False
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.store.mark_sent(uid, "sent_mqtt", "mqtt:accepted")
                sent += 1
            else:
                self.store.mark_attempt(uid, str(result.rc))
        return sent

    def _send_lora_summary(self, aggregate: dict[str, Any]) -> bool:
        summary = {
            "schema_version": aggregate["schema_version"],
            "message_uid": aggregate["message_uid"],
            "message_type": "emergency_event" if aggregate["priority"] != "normal" else "telemetry_summary",
            "delivery_status": "emergency" if aggregate["priority"] != "normal" else "offline_summary",
            "building_code": aggregate["building_code"],
            "generated_at": aggregate["generated_at"],
            "sequence_number": aggregate["sequence_number"],
            "priority": aggregate["priority"],
            "bridges": aggregate["bridges"],
        }
        result = self.lora.transmit(json.dumps(summary, separators=(",", ":")))
        self.store.log("INFO", f"LoRa {result.reason} latency_ms={result.latency_ms}")
        return result.success

    def ingest(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        if not readings:
            raise ValueError("El bridge necesita al menos una lectura")
        inserted = self.store.save_readings(readings)
        self.sequence += 1
        aggregate = aggregate_readings(
            readings, self.args.building_code, self.args.interval, self.sequence,
            self.args.node_catalog,
        )
        self.store.save_aggregate(aggregate)
        realtime_sent = self._send_rest(aggregate["message_uid"], aggregate)
        mqtt_catch_up = self._send_mqtt_pending()
        lora_sent = False
        if not realtime_sent and not mqtt_catch_up:
            lora_sent = self._send_lora_summary(aggregate)
        result = {
            "accepted": True,
            "raw_inserted": inserted,
            "message_uid": aggregate["message_uid"],
            "rest_realtime": realtime_sent,
            "mqtt_catch_up": mqtt_catch_up,
            "lora_summary": lora_sent,
            "storage": self.store.counts(),
        }
        self.store.log("INFO", json.dumps(result, ensure_ascii=False))
        return result

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "component": "bridge", "storage": self.store.counts()}

    def close(self) -> None:
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        self.store.close()


class Handler(BaseHTTPRequestHandler):
    runtime: BridgeRuntime

    def _write(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, self.runtime.health())
        else:
            self._write(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/readings":
            self._write(404, {"detail": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            readings = body["readings"] if isinstance(body, dict) else body
            if not isinstance(readings, list):
                raise ValueError("readings debe ser una lista")
            self._write(202, self.runtime.ingest(readings))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._write(400, {"detail": str(exc)})
        except Exception as exc:  # Mantiene el proceso activo ante una mala lectura.
            self.runtime.store.log("ERROR", repr(exc))
            self._write(500, {"detail": "Bridge processing error"})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"bridge-http | {fmt % args}")


def catalog() -> dict[str, dict[str, Any]]:
    return {
        "NODE-FLOOR-1": {"zone_id": "ZONE-F1", "floor": 1, "bridge_name": "Bridge 1 - Piso 1"},
        "NODE-FLOOR-2": {"zone_id": "ZONE-F2", "floor": 2, "bridge_name": "Bridge 2 - Piso 2"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel bridge simulator")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=8766)
    parser.add_argument("--building-code", default="SB-001")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--data-dir", default="data_bridge")
    parser.add_argument("--api-url", default=os.getenv("SENTINEL_API_URL"))
    parser.add_argument("--api-token", default=os.getenv("SENTINEL_API_TOKEN"))
    parser.add_argument("--api-timeout", type=float, default=10.0)
    parser.add_argument("--mqtt-host", default=os.getenv("SENTINEL_MQTT_HOST"))
    parser.add_argument("--mqtt-port", type=int, default=int(os.getenv("SENTINEL_MQTT_PORT", "8883")))
    parser.add_argument("--mqtt-username", default=os.getenv("SENTINEL_MQTT_USERNAME"))
    parser.add_argument("--mqtt-password", default=os.getenv("SENTINEL_MQTT_PASSWORD"))
    parser.add_argument("--mqtt-tls", action="store_true")
    parser.add_argument("--mqtt-ca-file", default=os.getenv("SENTINEL_MQTT_CA_FILE"))
    parser.add_argument("--lora-loss-rate", type=float, default=0.0)
    parser.add_argument("--lora-min-delay-ms", type=int, default=100)
    parser.add_argument("--lora-max-delay-ms", type=int, default=400)
    parser.add_argument("--lora-max-payload-bytes", type=int, default=1200)
    parser.add_argument("--lora-seed", type=int, default=None)
    args = parser.parse_args()
    args.node_catalog = catalog()
    runtime = BridgeRuntime(args)
    Handler.runtime = runtime
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), Handler)
    print(f"Bridge iniciado | http://{args.listen_host}:{args.listen_port} | data={args.data_dir}")
    print("POST /v1/readings para recibir lecturas; GET /health para verificarlo")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.close()
        print("Bridge detenido; la base local permanece guardada.")


if __name__ == "__main__":
    main()
