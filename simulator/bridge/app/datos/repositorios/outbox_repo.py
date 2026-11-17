import json
from typing import Any

from app.core.tiempo import now_utc
from app.datos.db import Database


class OutboxRepo:
    """Tabla aggregate_outbox: mensajes agregados pendientes o ya entregados."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def save_aggregate(self, aggregate: dict[str, Any]) -> None:
        with self._db.lock:
            self._db.con.execute(
                """INSERT OR IGNORE INTO aggregate_outbox
                (message_uid, generated_at, payload_json)
                VALUES (?, ?, ?)""",
                (
                    aggregate["message_uid"], aggregate["generated_at"],
                    json.dumps(aggregate, ensure_ascii=False),
                ),
            )
            self._db.con.commit()

    def pending(self, limit: int = 50) -> list[tuple[str, str, int]]:
        with self._db.lock:
            return self._db.con.execute(
                """SELECT message_uid, payload_json, attempts
                FROM aggregate_outbox WHERE status='pending'
                ORDER BY generated_at LIMIT ?""", (limit,)
            ).fetchall()

    def mark_sent(self, uid: str, status: str, response: str) -> None:
        with self._db.lock:
            self._db.con.execute(
                """UPDATE aggregate_outbox
                SET status=?, attempts=attempts+1, last_attempt_at=?,
                    sent_at=?, response=? WHERE message_uid=?""",
                (status, now_utc(), now_utc(), response, uid),
            )
            self._db.con.commit()

    def mark_attempt(self, uid: str, response: str) -> None:
        with self._db.lock:
            self._db.con.execute(
                """UPDATE aggregate_outbox SET attempts=attempts+1,
                last_attempt_at=?, response=? WHERE message_uid=?""",
                (now_utc(), response, uid),
            )
            self._db.con.commit()

    def counts(self) -> dict[str, int]:
        with self._db.lock:
            pending = self._db.con.execute(
                "SELECT COUNT(*) FROM aggregate_outbox WHERE status='pending'"
            ).fetchone()[0]
            sent = self._db.con.execute(
                "SELECT COUNT(*) FROM aggregate_outbox WHERE status <> 'pending'"
            ).fetchone()[0]
        return {"pending": pending, "sent": sent}
