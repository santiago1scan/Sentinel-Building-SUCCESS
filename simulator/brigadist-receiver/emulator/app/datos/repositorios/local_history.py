from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LocalHistory:
    """Historial corto; físicamente se reemplaza por NVS/LittleFS."""

    def __init__(self, path: Path, limit: int = 100) -> None:
        self.path = path
        self.limit = limit

    def save(self, alerts: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(alerts[: self.limit], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
