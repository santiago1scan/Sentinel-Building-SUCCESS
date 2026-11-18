from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class BridgeClient:
    """Única frontera entre el simulador y un bridge independiente."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Bridge HTTP {exc.code}: {detail}") from exc

    def ingest(self, events: list[dict[str, Any]], window_seconds: float) -> dict[str, Any]:
        return self._post("/api/ingest", {"events": events, "window_seconds": window_seconds})

    def control(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/control", body)

    def state(self) -> dict[str, Any]:
        return self._get("/api/state")

    def status(self) -> dict[str, Any]:
        return self._get("/api/control/status")
