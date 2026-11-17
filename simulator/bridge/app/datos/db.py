"""Conexión SQLite y esquema. Mismo esquema que bridge_service.py para poder
reutilizar un bridge_local.db existente sin migrar datos."""

import sqlite3
import threading
from pathlib import Path

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
CREATE TABLE IF NOT EXISTS node_registration (
    node_code TEXT PRIMARY KEY,
    registration_id TEXT NOT NULL,
    poll_secret TEXT NOT NULL,
    name TEXT NOT NULL,
    building_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    requested_at TEXT NOT NULL,
    expires_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS node_credential (
    node_code TEXT PRIMARY KEY,
    node_id INTEGER,
    token TEXT NOT NULL,
    obtained_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA synchronous=FULL")
        self.con.execute("PRAGMA busy_timeout=5000")
        self.con.executescript(SCHEMA)
        self.con.commit()
        self.lock = threading.Lock()

    def close(self) -> None:
        self.con.close()
