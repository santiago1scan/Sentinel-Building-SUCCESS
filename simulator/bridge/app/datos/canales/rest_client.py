"""Transporte REST hacia el backend central. Solo entrega; no decide nada del negocio."""

import json
import urllib.error
import urllib.request
from typing import Any


class RestClient:
    def __init__(self, base_url: str | None, path: str, timeout: float) -> None:
        self.base_url = base_url
        self.path = path
        self.timeout = timeout

    @property
    def configurado(self) -> bool:
        return bool(self.base_url)

    def enviar(self, payload: dict[str, Any], token: str) -> tuple[bool, str]:
        """POST del agregado con el token del nodo. Devuelve (entregado, detalle)."""
        request = urllib.request.Request(
            self.base_url.rstrip("/") + self.path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Node-Token": token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                if 200 <= response.status < 300:
                    return True, body
                return False, f"HTTP {response.status}: {body}"
        except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            return False, str(exc)
