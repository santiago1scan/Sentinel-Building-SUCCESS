"""Canal opcional hacia la simulación Beta: refleja en ella las anomalías de este panel.

Beta es una simulación aparte (dashboard en :8782, API de control en :8792). Este cliente solo usa su
API de control: `POST /api/control {"action": "anomaly", "target": nodo, "sensor": tipo, "value": bool}`.
"""

import json
import urllib.error
import urllib.request


class ClienteBetaError(Exception):
    """Beta no respondió o rechazó el comando."""


class ClienteBeta:
    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    @property
    def configurado(self) -> bool:
        return bool(self.base_url)

    def anomalia(self, nodo: str, tipo_sensor: str, activa: bool) -> None:
        peticion = urllib.request.Request(
            self.base_url + "/api/control",
            data=json.dumps({"action": "anomaly", "target": nodo,
                             "sensor": tipo_sensor, "value": activa}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                cuerpo = json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="replace")[:200]
            exc.close()
            raise ClienteBetaError(f"HTTP {exc.code}: {detalle}") from exc
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ClienteBetaError(str(exc)) from exc
        if not cuerpo.get("ok"):
            raise ClienteBetaError(f"Beta rechazó el comando: {cuerpo}")
