"""Registro del nodo en el backend: la solicitud en curso y la credencial obtenida.

El poll_secret y el token son secretos de este bridge: viven solo en esta base local y
nunca se devuelven por la API.
"""

from typing import Any

from app.core.tiempo import now_utc
from app.datos.db import Database

_COLUMNAS = ("node_code", "registration_id", "poll_secret", "name", "building_id", "zone_id",
             "status", "detail", "requested_at", "expires_at", "updated_at")


class RegistroRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def obtener(self, codigo: str) -> dict[str, Any] | None:
        with self._db.lock:
            fila = self._db.con.execute(
                f"SELECT {', '.join(_COLUMNAS)} FROM node_registration WHERE node_code = ?",
                (codigo,),
            ).fetchone()
        return None if fila is None else dict(zip(_COLUMNAS, fila))

    def guardar_solicitud(self, *, codigo: str, registration_id: str, poll_secret: str,
                          nombre: str, building_id: int, zone_id: int,
                          expires_at: str | None) -> None:
        ahora = now_utc()
        with self._db.lock:
            self._db.con.execute(
                """INSERT OR REPLACE INTO node_registration
                (node_code, registration_id, poll_secret, name, building_id, zone_id,
                 status, detail, requested_at, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
                (codigo, registration_id, poll_secret, nombre, building_id, zone_id,
                 "Esperando aprobación del administrador", ahora, expires_at, ahora),
            )
            self._db.con.commit()

    def actualizar(self, codigo: str, estado: str, detalle: str, *,
                   limpiar_secreto: bool = False) -> None:
        with self._db.lock:
            self._db.con.execute(
                """UPDATE node_registration
                SET status = ?, detail = ?, updated_at = ?,
                    poll_secret = CASE WHEN ? THEN '' ELSE poll_secret END
                WHERE node_code = ?""",
                (estado, detalle, now_utc(), int(limpiar_secreto), codigo),
            )
            self._db.con.commit()

    def guardar_credencial(self, codigo: str, node_id: int | None, token: str) -> None:
        with self._db.lock:
            self._db.con.execute(
                """INSERT OR REPLACE INTO node_credential (node_code, node_id, token, obtained_at)
                VALUES (?, ?, ?, ?)""",
                (codigo, node_id, token, now_utc()),
            )
            self._db.con.commit()

    def credenciales(self) -> dict[str, str]:
        with self._db.lock:
            filas = self._db.con.execute("SELECT node_code, token FROM node_credential").fetchall()
        return {codigo: token for codigo, token in filas}

    def tiene_credencial(self, codigo: str) -> bool:
        with self._db.lock:
            return self._db.con.execute(
                "SELECT 1 FROM node_credential WHERE node_code = ?", (codigo,)
            ).fetchone() is not None
