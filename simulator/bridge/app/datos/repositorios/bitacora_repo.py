from app.core.tiempo import now_utc
from app.datos.db import Database


class BitacoraRepo:
    """Tabla bridge_log: eventos del bridge para diagnóstico."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def log(self, level: str, detail: str) -> None:
        with self._db.lock:
            self._db.con.execute(
                "INSERT INTO bridge_log(logged_at, level, detail) VALUES (?, ?, ?)",
                (now_utc(), level, detail),
            )
            self._db.con.commit()
