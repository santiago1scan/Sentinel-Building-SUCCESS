"""Caja negra local de prueba para recibir el JSON estandarizado por REST."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException

DATA_DIR = Path(os.getenv("SENTINEL_API_DATA_DIR", "data_api"))
DB_PATH = DATA_DIR / "api_received.db"
API_TOKEN = os.getenv("SENTINEL_API_TOKEN", "")
DB_INITIALIZATION_LOCK = threading.Lock()
MAX_READING_AGE_SECONDS = 90

app = FastAPI(title="Sentinel Black Box API", version="1.0.0")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    with DB_INITIALIZATION_LOCK:
        con.executescript("""CREATE TABLE IF NOT EXISTS received_message (
            message_uid TEXT PRIMARY KEY,
            message_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            received_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sensor_state (
            schema_version TEXT NOT NULL,
            node_code TEXT NOT NULL,
            measurement_type TEXT NOT NULL,
            floor INTEGER,
            priority TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            message_uid TEXT NOT NULL,
            sensor_json TEXT NOT NULL,
            PRIMARY KEY (schema_version, node_code, measurement_type)
        );
        CREATE TABLE IF NOT EXISTS backend_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );""")
        con.commit()
        migrated = con.execute(
            "SELECT 1 FROM backend_metadata WHERE key='sensor_state_v1'"
        ).fetchone()
        if not migrated:
            for payload_json, received_at in con.execute(
                "SELECT payload_json, received_at FROM received_message ORDER BY received_at"
            ).fetchall():
                _store_sensor_state(con, json.loads(payload_json), received_at)
            con.execute(
                "INSERT INTO backend_metadata (key, value) VALUES ('sensor_state_v1', 'complete')"
            )
            con.commit()
    return con


def _store_sensor_state(
    con: sqlite3.Connection,
    payload: dict[str, Any],
    received_at: str,
) -> None:
    schema_version = str(payload.get("schema_version", ""))
    generated_at = str(payload.get("generated_at") or received_at)
    priority = str(payload.get("priority", "normal"))
    message_uid = str(payload.get("message_uid", ""))
    for bridge in payload.get("bridges", []):
        if not isinstance(bridge, dict):
            continue
        node_code = bridge.get("node_code") or bridge.get("node_uid")
        sensors = bridge.get("sensors", [])
        if not isinstance(node_code, str) or not isinstance(sensors, list):
            continue
        for sensor in sensors:
            if not isinstance(sensor, dict):
                continue
            measurement_type = sensor.get("measurement_type")
            if not isinstance(measurement_type, str) or not measurement_type:
                continue
            con.execute(
                """INSERT INTO sensor_state
                   (schema_version, node_code, measurement_type, floor, priority,
                    generated_at, message_uid, sensor_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(schema_version, node_code, measurement_type)
                   DO UPDATE SET floor=excluded.floor, priority=excluded.priority,
                       generated_at=excluded.generated_at, message_uid=excluded.message_uid,
                       sensor_json=excluded.sensor_json
                   WHERE excluded.generated_at >= sensor_state.generated_at""",
                (
                    schema_version,
                    node_code,
                    measurement_type,
                    bridge.get("floor"),
                    priority,
                    generated_at,
                    message_uid,
                    json.dumps(sensor, ensure_ascii=False),
                ),
            )


def sensor_health_rank(sensor: dict[str, Any]) -> int:
    data = sensor.get("data") or {}
    measurement_type = sensor.get("measurement_type")
    try:
        if measurement_type == "motion":
            value = float(data.get("rms_max_g") or 0)
            return 2 if value >= 0.25 else 1 if value >= 0.05 else 0
        if measurement_type == "temperature":
            value = float(data.get("maximum_c") or 0)
            return 2 if value >= 40 else 1 if value >= 30 else 0
        if measurement_type == "air_quality":
            value = float(data.get("iaq_avg") or 0)
            return 2 if value >= 250 else 1 if value >= 120 else 0
        if measurement_type == "electrical":
            value = float(data.get("voltage_avg_v") or 0)
            return 2 if data.get("battery_low") or value < 11 else 1 if value < 11.8 else 0
    except (AttributeError, TypeError, ValueError):
        return 0
    return 0


def latest_sensor_readings(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """SELECT schema_version, node_code, measurement_type, floor, priority,
                  generated_at, message_uid, sensor_json
           FROM sensor_state"""
    ).fetchall()
    now = datetime.now(timezone.utc)
    chosen: dict[tuple[str, str], tuple[int, tuple[Any, ...], bool]] = {}
    for row in rows:
        key = (row[1], row[2])
        current = chosen.get(key)
        sensor = json.loads(row[7])
        try:
            generated_at = datetime.fromisoformat(row[5].replace("Z", "+00:00"))
            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            stale = (now - generated_at).total_seconds() > MAX_READING_AGE_SECONDS
        except ValueError:
            stale = True
        rank = 0 if stale else sensor_health_rank(sensor)
        current_rank = current[0] if current else -1
        if current is None or (rank, row[5]) > (current_rank, current[1][5]):
            chosen[key] = (rank, row, stale)

    readings = []
    for _, row, stale in chosen.values():
        sensor = json.loads(row[7])
        sensor.update(
            node=row[1],
            floor=row[3],
            priority=row[4],
            generated_at=row[5],
            source="scenario" if row[0] == "1.0" else "beta" if row[0] == "2.0" else "mock",
            message_uid=row[6],
            stale=stale,
        )
        readings.append(sensor)
    return sorted(readings, key=lambda sensor: (sensor["node"], sensor["measurement_type"]))


def validate_token(authorization: str | None) -> None:
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Token invalido")


def receive_message(payload: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    validate_token(authorization)
    if payload.get("schema_version") not in {"1.0", "2.0"}:
        raise HTTPException(status_code=422, detail="schema_version no soportada")
    if payload.get("message_type") not in {
        "telemetry_aggregate", "telemetry_summary", "emergency_event"
    }:
        raise HTTPException(status_code=422, detail="message_type no soportado")
    bridges = payload.get("bridges")
    if not payload.get("message_uid") or not isinstance(bridges, list) or not bridges:
        raise HTTPException(status_code=422, detail="Faltan message_uid o bridges")
    readings_created = sum(
        len(bridge.get("sensors", []))
        for bridge in bridges
        if isinstance(bridge, dict) and isinstance(bridge.get("sensors", []), list)
    )
    if readings_created == 0:
        raise HTTPException(status_code=422, detail="El agregado no contiene sensores")
    con = db()
    uid = str(payload["message_uid"])
    duplicate = con.execute("SELECT 1 FROM received_message WHERE message_uid=?", (uid,)).fetchone()
    if duplicate:
        con.close()
        return {
            "accepted": True,
            "duplicate": True,
            "message_uid": uid,
            "readings_created": readings_created,
            "errors": [],
        }
    received_at = now_utc()
    con.execute("INSERT INTO received_message VALUES (?,?,?,?,?)", (
        uid, payload["message_type"], payload.get("priority", "normal"),
        received_at, json.dumps(payload, ensure_ascii=False)))
    _store_sensor_state(con, payload, received_at)
    con.commit()
    con.close()
    return {
        "accepted": True,
        "duplicate": False,
        "message_uid": uid,
        "readings_created": readings_created,
        "errors": [],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/telemetry/aggregate", status_code=202)
def telemetry_aggregate(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return receive_message(payload, authorization)


@app.post("/api/v1/telemetry/realtime", status_code=202)
def telemetry_realtime(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Alias explícito para lecturas nuevas enviadas por REST."""
    payload["delivery_status"] = "realtime"
    payload["transport"] = "rest"
    return receive_message(payload, authorization)


@app.post("/api/v1/events/emergency", status_code=202)
def emergency(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    payload["message_type"] = "emergency_event"
    return receive_message(payload, authorization)


@app.get("/api/v1/last")
def last_message(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    validate_token(authorization)
    con = db()
    row = con.execute("SELECT payload_json FROM received_message ORDER BY received_at DESC LIMIT 1").fetchone()
    con.close()
    return json.loads(row[0]) if row else {"message": "sin datos"}


@app.get("/api/v1/sensors/latest")
def latest_sensors(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    validate_token(authorization)
    con = db()
    try:
        return {"source": "shared_mock_sqlite", "sensors": latest_sensor_readings(con)}
    finally:
        con.close()
