"""Caja negra local de prueba para recibir el JSON estandarizado por REST."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException

DATA_DIR = Path(os.getenv("SENTINEL_API_DATA_DIR", "data_api"))
DB_PATH = DATA_DIR / "api_received.db"
API_TOKEN = os.getenv("SENTINEL_API_TOKEN", "")

app = FastAPI(title="Sentinel Black Box API", version="1.0.0")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS received_message (
        message_uid TEXT PRIMARY KEY,
        message_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        received_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )""")
    con.commit()
    return con


def validate_token(authorization: str | None) -> None:
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Token invalido")


def receive_message(payload: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    validate_token(authorization)
    if payload.get("schema_version") != "1.0":
        raise HTTPException(status_code=422, detail="schema_version no soportada")
    if payload.get("message_type") not in {"telemetry_aggregate", "emergency_event"}:
        raise HTTPException(status_code=422, detail="message_type no soportado")
    if not payload.get("message_uid") or not payload.get("bridges"):
        raise HTTPException(status_code=422, detail="Faltan message_uid o bridges")
    if payload.get("delivery_status") not in {
        "pending", "realtime", "realtime_fallback", "catch_up"
    }:
        raise HTTPException(status_code=422, detail="delivery_status no soportado")
    con = db()
    uid = str(payload["message_uid"])
    duplicate = con.execute("SELECT 1 FROM received_message WHERE message_uid=?", (uid,)).fetchone()
    if duplicate:
        con.close()
        return {"accepted": True, "duplicate": True, "message_uid": uid}
    con.execute("INSERT INTO received_message VALUES (?,?,?,?,?)", (
        uid, payload["message_type"], payload.get("priority", "normal"),
        now_utc(), json.dumps(payload, ensure_ascii=False)))
    con.commit()
    con.close()
    return {"accepted": True, "duplicate": False, "message_uid": uid}


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
