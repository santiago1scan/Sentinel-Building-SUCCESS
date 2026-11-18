from typing import Any

from app.core.tiempo import now_utc
from app.datos.db import Database


class IncidenteRepo:
    """Tabla incident: emergencias en curso por nodo. Sobrevive a reinicios del bridge."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def abierto(self, nodo: str) -> dict[str, Any] | None:
        with self._db.lock:
            fila = self._db.con.execute(
                "SELECT id, normal_streak FROM incident WHERE node_code=? AND status='open'",
                (nodo,)).fetchone()
        return {"id": fila[0], "normal_streak": fila[1]} if fila else None

    def abrir(self, nodo: str, started_at: str, started_rowid: int, context_from_rowid: int) -> int:
        with self._db.lock:
            cursor = self._db.con.execute(
                """INSERT INTO incident
                (node_code, started_at, started_rowid, context_from_rowid) VALUES (?, ?, ?, ?)""",
                (nodo, started_at, started_rowid, context_from_rowid))
            self._db.con.commit()
            return cursor.lastrowid

    def emergencia_continua(self, incidente_id: int) -> None:
        with self._db.lock:
            self._db.con.execute("UPDATE incident SET normal_streak=0 WHERE id=?", (incidente_id,))
            self._db.con.commit()

    def bloque_normal(self, incidente_id: int, cierre: int) -> bool:
        """Cuenta un bloque normal seguido. Cierra el incidente al llegar a `cierre`."""
        with self._db.lock:
            self._db.con.execute(
                "UPDATE incident SET normal_streak=normal_streak+1 WHERE id=?", (incidente_id,))
            racha = self._db.con.execute(
                "SELECT normal_streak FROM incident WHERE id=?", (incidente_id,)).fetchone()[0]
            cerrado = racha >= cierre
            if cerrado:
                self._db.con.execute(
                    "UPDATE incident SET status='closed', closed_at=? WHERE id=?",
                    (now_utc(), incidente_id))
            self._db.con.commit()
        return cerrado

    def con_contexto_pendiente(self) -> list[dict[str, Any]]:
        with self._db.lock:
            filas = self._db.con.execute(
                """SELECT id, node_code, context_from_rowid, started_rowid FROM incident
                WHERE context_sent=0 ORDER BY id""").fetchall()
        return [{"id": f[0], "node_code": f[1], "context_from": f[2], "started_rowid": f[3]}
                for f in filas]

    def contexto_enviado(self, incidente_id: int) -> None:
        with self._db.lock:
            self._db.con.execute("UPDATE incident SET context_sent=1 WHERE id=?", (incidente_id,))
            self._db.con.commit()
