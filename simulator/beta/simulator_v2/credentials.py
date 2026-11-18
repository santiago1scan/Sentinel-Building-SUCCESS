"""Credenciales y solicitudes de registro de los nodos, compartidas entre procesos.

El dashboard (que atiende /perfil) escribe aquí el token que entrega consulta; el simulador
lo lee en cada envío REST, así que el nodo empieza a usarlo sin reiniciar. El archivo contiene
secretos (poll_secret y token): se crea con permisos 0600 y nunca se devuelve por la API.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class NodeRegistryStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._cache: dict[str, Any] = {"credentials": {}, "requests": {}}
        self._mtime: int | None = None

    def _load(self) -> dict[str, Any]:
        with self._lock:
            try:
                mtime = self.path.stat().st_mtime_ns
            except FileNotFoundError:
                self._cache, self._mtime = {"credentials": {}, "requests": {}}, None
                return self._cache
            if mtime != self._mtime:
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    data = {}
                self._cache = {
                    "credentials": dict(data.get("credentials", {})),
                    "requests": dict(data.get("requests", {})),
                }
                self._mtime = mtime
            return self._cache

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp, self.path)
        self._mtime = None  # fuerza releer en la siguiente consulta

    # -- credenciales ---------------------------------------------------------------------
    def token_for(self, node_code: str) -> str:
        return str(self._load()["credentials"].get(node_code, {}).get("token", ""))

    def has_credential(self, node_code: str) -> bool:
        return bool(self.token_for(node_code))

    def save_credential(self, node_code: str, node_id: int | None, token: str) -> None:
        with self._lock:
            data = json.loads(json.dumps(self._load()))
            data["credentials"][node_code] = {
                "node_id": node_id, "token": token, "obtained_at": _now(),
            }
            self._write(data)

    # -- solicitudes de registro ----------------------------------------------------------
    def get_request(self, node_code: str) -> dict[str, Any] | None:
        request = self._load()["requests"].get(node_code)
        return dict(request) if request else None

    def save_request(self, node_code: str, **fields: Any) -> None:
        with self._lock:
            data = json.loads(json.dumps(self._load()))
            now = _now()
            data["requests"][node_code] = {
                **fields, "status": "pending", "detail": "Esperando aprobación del administrador",
                "requested_at": now, "updated_at": now,
            }
            self._write(data)

    def update_request(self, node_code: str, status: str, detail: str, *,
                       clear_secret: bool = False) -> None:
        with self._lock:
            data = json.loads(json.dumps(self._load()))
            request = data["requests"].get(node_code)
            if request is None:
                return
            request.update(status=status, detail=detail, updated_at=_now())
            if clear_secret:
                request["poll_secret"] = ""
            self._write(data)
