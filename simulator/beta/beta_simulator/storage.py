from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class LocalStore:
    """Persistent local store for one bridge or the external gateway."""

    def __init__(self, path: Path, capacity_gb: float, limit_ratio: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.capacity_bytes = int(capacity_gb * 1024**3)
        self.limit_bytes = int(self.capacity_bytes * limit_ratio)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_readings (
                event_id TEXT PRIMARY KEY,
                node_code TEXT NOT NULL,
                sensor_code TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                received_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_raw_node_time
                ON raw_readings(node_code, generated_at);
            CREATE TABLE IF NOT EXISTS aggregates (
                message_uid TEXT PRIMARY KEY,
                node_code TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT,
                response TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_aggregates_status
                ON aggregates(status, generated_at);
            CREATE TABLE IF NOT EXISTS gateway_messages (
                message_uid TEXT PRIMARY KEY,
                node_code TEXT NOT NULL,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                backend_status TEXT NOT NULL DEFAULT 'pending'
            );
            """
        )
        self.db.commit()

    def save_raw(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.db.execute(
                """
                INSERT OR IGNORE INTO raw_readings
                (event_id, node_code, sensor_code, sensor_type, generated_at,
                 sequence_number, payload_json, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    event["event_id"], event["node_code"], event["sensor_code"],
                    event["sensor_type"], event["generated_at"],
                    event["sequence_number"], json.dumps(event, separators=(",", ":")),
                ),
            )
            self.db.commit()

    def save_aggregate(self, payload: dict[str, Any], node_code: str) -> None:
        with self.lock:
            self.db.execute(
                """
                INSERT OR IGNORE INTO aggregates
                (message_uid, node_code, generated_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload["message_uid"], node_code, payload["generated_at"],
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            self.db.commit()

    def mark_aggregate(self, message_uid: str, status: str, response: str = "") -> None:
        with self.lock:
            self.db.execute(
                """UPDATE aggregates SET status=?, attempts=attempts+1,
                   last_attempt_at=datetime('now'), response=? WHERE message_uid=?""",
                (status, response, message_uid),
            )
            self.db.commit()

    def pending_aggregates(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute(
                "SELECT message_uid, node_code, payload_json, attempts FROM aggregates "
                "WHERE status='pending' ORDER BY generated_at"
            ).fetchall()
        return [
            {"message_uid": uid, "node_code": node, "payload": json.loads(payload), "attempts": attempts}
            for uid, node, payload, attempts in rows
        ]

    def pending_gateway_messages(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute(
                "SELECT message_uid, node_code, payload_json FROM gateway_messages "
                "WHERE backend_status='pending' ORDER BY received_at"
            ).fetchall()
        return [
            {"message_uid": uid, "node_code": node, "payload": json.loads(payload)}
            for uid, node, payload in rows
        ]

    def mark_gateway_message(self, message_uid: str, status: str) -> None:
        with self.lock:
            self.db.execute(
                "UPDATE gateway_messages SET backend_status=? WHERE message_uid=?",
                (status, message_uid),
            )
            self.db.commit()

    def receive_gateway_message(self, payload: dict[str, Any], received_at: str) -> bool:
        with self.lock:
            before = self.db.total_changes
            self.db.execute(
                """INSERT OR IGNORE INTO gateway_messages
                   (message_uid, node_code, received_at, payload_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    payload["message_uid"],
                    payload["bridges"][0]["node_code"],
                    received_at,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            self.db.commit()
            return self.db.total_changes > before

    def status(self) -> dict[str, Any]:
        with self.lock:
            raw = self.db.execute("SELECT COUNT(*) FROM raw_readings").fetchone()[0]
            aggregates = self.db.execute("SELECT COUNT(*) FROM aggregates").fetchone()[0]
            pending = self.db.execute(
                "SELECT COUNT(*) FROM aggregates WHERE status='pending'"
            ).fetchone()[0]
            gateway = self.db.execute("SELECT COUNT(*) FROM gateway_messages").fetchone()[0]
            self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")
            self.db.commit()
        used = self.path.stat().st_size if self.path.exists() else 0
        return {
            "raw_readings": raw,
            "aggregates": aggregates,
            "pending": pending,
            "gateway_messages": gateway,
            "used_bytes": used,
            "limit_bytes": self.limit_bytes,
            "usage_ratio": round(used / self.capacity_bytes, 6) if self.capacity_bytes else 0,
            "limit_ratio": round(used / self.limit_bytes, 6) if self.limit_bytes else 0,
        }

    def close(self) -> None:
        with self.lock:
            self.db.close()

