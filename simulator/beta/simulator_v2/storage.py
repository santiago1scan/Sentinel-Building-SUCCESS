from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class StorageLimitReached(RuntimeError):
    """Raised when only pending data remains and the local store is full."""


class StorageWriteError(RuntimeError):
    """Raised when a local SQLite write cannot be committed."""


class SummaryStore:
    """Persistent local store for summaries, emergencies and sync evidence.

    Raw sensor readings are intentionally not persisted. They exist only in
    the bridge processing window and are discarded after aggregation.
    """

    def __init__(self, path: Path, capacity_gb: float = 128.0, limit_ratio: float = 0.70) -> None:
        if capacity_gb <= 0:
            raise ValueError("capacity_gb must be positive")
        if not 0 < limit_ratio <= 1:
            raise ValueError("limit_ratio must be between 0 and 1")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.capacity_bytes = int(capacity_gb * 1024**3)
        self.limit_bytes = int(self.capacity_bytes * limit_ratio)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                message_uid TEXT PRIMARY KEY,
                node_code TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                delivery_status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT,
                response TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_summaries_status
                ON summaries(delivery_status, generated_at);
            CREATE TABLE IF NOT EXISTS emergency_events (
                event_uid TEXT PRIMARY KEY,
                node_code TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_uid TEXT NOT NULL,
                node_code TEXT NOT NULL,
                transport TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        # LoRa only confirms that the external receiver has a backup copy;
        # it does not confirm delivery to the backend.
        self.db.execute(
            "UPDATE summaries SET delivery_status='pending_backend' "
            "WHERE delivery_status='sent_lora'"
        )
        self.db.commit()

    def _checkpoint(self) -> None:
        self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")

    def used_bytes(self) -> int:
        with self.lock:
            self._checkpoint()
            total = 0
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(f"{self.path}{suffix}")
                if candidate.exists():
                    total += candidate.stat().st_size
            return total

    def _rotate_sent(self, required_bytes: int = 0) -> int:
        """Delete oldest delivered summaries until the next write fits."""
        deleted = 0
        while self.used_bytes() + required_bytes > self.limit_bytes:
            row = self.db.execute(
                """SELECT message_uid FROM summaries
                   WHERE delivery_status NOT IN ('pending', 'pending_backend')
                   ORDER BY generated_at ASC LIMIT 1"""
            ).fetchone()
            if row is None:
                raise StorageLimitReached(
                    "Local storage limit reached; pending summaries are protected"
                )
            self.db.execute("DELETE FROM summaries WHERE message_uid=?", (row[0],))
            deleted += 1
            self.db.commit()
            # Deleting rows does not immediately reduce a SQLite file. Compact
            # the local store so the configured percentage represents physical
            # disk usage, not only logical row count.
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.execute("VACUUM")
        return deleted

    def enforce_limit(self, required_bytes: int = 0) -> int:
        with self.lock:
            deleted = self._rotate_sent(required_bytes)
            self.db.commit()
            return deleted

    def save_summary(self, payload: dict[str, Any], node_code: str) -> bool:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self.lock:
            try:
                exists = self.db.execute(
                    "SELECT 1 FROM summaries WHERE message_uid=?", (payload["message_uid"],)
                ).fetchone()
                if exists:
                    return False
                self._rotate_sent(len(encoded.encode("utf-8")))
                self.db.execute(
                    """INSERT INTO summaries
                       (message_uid, node_code, generated_at, payload_json)
                       VALUES (?, ?, ?, ?)""",
                    (payload["message_uid"], node_code, payload["generated_at"], encoded),
                )
                self.db.commit()
                return True
            except StorageLimitReached:
                self.db.rollback()
                raise
            except (KeyError, sqlite3.Error, OSError) as exc:
                self.db.rollback()
                raise StorageWriteError(str(exc)) from exc

    def save_emergency(self, event: dict[str, Any]) -> bool:
        encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self.lock:
            try:
                self._rotate_sent(len(encoded.encode("utf-8")))
                cursor = self.db.execute(
                    """INSERT OR IGNORE INTO emergency_events
                       (event_uid, node_code, generated_at, payload_json)
                       VALUES (?, ?, ?, ?)""",
                    (event["event_uid"], event["node_code"], event["generated_at"], encoded),
                )
                self.db.commit()
                return cursor.rowcount == 1
            except StorageLimitReached:
                self.db.rollback()
                raise
            except (KeyError, sqlite3.Error, OSError) as exc:
                self.db.rollback()
                raise StorageWriteError(str(exc)) from exc

    def mark_summary(self, message_uid: str, status: str, response: str = "") -> None:
        with self.lock:
            try:
                self.db.execute(
                    """UPDATE summaries SET delivery_status=?, attempts=attempts+1,
                       last_attempt_at=datetime('now'), response=? WHERE message_uid=?""",
                    (status, response[:2000], message_uid),
                )
                self.db.commit()
            except sqlite3.Error as exc:
                self.db.rollback()
                raise StorageWriteError(str(exc)) from exc

    def pending_summaries(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute(
                """SELECT message_uid, node_code, payload_json, attempts, delivery_status
                   FROM summaries
                   WHERE delivery_status IN ('pending', 'pending_backend')
                   ORDER BY generated_at ASC, rowid ASC"""
            ).fetchall()
        return [
            {"message_uid": uid, "node_code": node, "payload": json.loads(payload),
             "attempts": attempts, "delivery_status": status}
            for uid, node, payload, attempts, status in rows
        ]

    def log_sync(self, message_uid: str, node_code: str, transport: str, result: str) -> None:
        with self.lock:
            try:
                self.db.execute(
                    "INSERT INTO sync_log(message_uid,node_code,transport,result) VALUES(?,?,?,?)",
                    (message_uid, node_code, transport, result),
                )
                self.db.commit()
            except sqlite3.Error:
                self.db.rollback()

    def status(self) -> dict[str, Any]:
        with self.lock:
            summaries = self.db.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
            pending = self.db.execute(
                "SELECT COUNT(*) FROM summaries "
                "WHERE delivery_status IN ('pending', 'pending_backend')"
            ).fetchone()[0]
            emergencies = self.db.execute("SELECT COUNT(*) FROM emergency_events").fetchone()[0]
            syncs = self.db.execute("SELECT COUNT(*) FROM sync_log").fetchone()[0]
            self._checkpoint()
            self.db.commit()
        used = self.used_bytes()
        return {
            "raw_readings_persisted": 0,
            "summaries": summaries,
            "pending": pending,
            "emergency_events": emergencies,
            "sync_log_entries": syncs,
            "used_bytes": used,
            "capacity_gb": self.capacity_bytes / 1024**3,
            "limit_ratio": self.limit_bytes / self.capacity_bytes,
            "limit_bytes": self.limit_bytes,
            "limit_reached": used >= self.limit_bytes,
        }

    def close(self) -> None:
        with self.lock:
            self.db.close()
