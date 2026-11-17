"""Consultas de solo lectura sobre raw_reading para las gráficas del nodo."""

from app.datos.db import Database


class GraficasRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    def serie(self, nodo: str, sensor: str, campo: str, desde_iso: str) -> list[tuple[str, float]]:
        """(hora, valor) de un campo del payload de un sensor. `campo` viene del registro, no del usuario."""
        with self._db.lock:
            filas = self._db.con.execute(
                """SELECT generated_at, json_extract(payload_json, ?)
                FROM raw_reading
                WHERE node_id = ? AND sensor_type = ? AND generated_at >= ?
                ORDER BY generated_at""",
                (f"$.payload.{campo}", nodo, sensor, desde_iso),
            ).fetchall()
        return [(hora, float(valor)) for hora, valor in filas if valor is not None]

    def prioridades_por_minuto(self, nodo: str, desde_iso: str) -> list[tuple[str, str, int]]:
        """(minuto 'AAAA-MM-DDTHH:MM', prioridad, cantidad) de las lecturas del nodo."""
        with self._db.lock:
            return self._db.con.execute(
                """SELECT substr(generated_at, 1, 16) AS minuto,
                          json_extract(payload_json, '$.priority') AS prioridad,
                          COUNT(*)
                FROM raw_reading
                WHERE node_id = ? AND generated_at >= ?
                GROUP BY minuto, prioridad
                ORDER BY minuto""",
                (nodo, desde_iso),
            ).fetchall()
