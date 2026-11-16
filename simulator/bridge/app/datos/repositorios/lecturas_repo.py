import json
from typing import Any

from app.core.tiempo import now_utc
from app.datos.db import Database


class LecturasRepo:
    """Tabla raw_reading: eventos originales, sin duplicar por event_id."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def save_readings(self, readings: list[dict[str, Any]]) -> int:
        inserted = 0
        with self._db.lock:
            for reading in readings:
                cursor = self._db.con.execute(
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
            self._db.con.commit()
        return inserted

    def count(self) -> int:
        with self._db.lock:
            return self._db.con.execute("SELECT COUNT(*) FROM raw_reading").fetchone()[0]
