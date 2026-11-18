"""Login con Firebase y registro de nodos para el dashboard de Beta.

Mismas rutas que el bridge principal: /login, /perfil, /auth/config, /auth/me y
/api/registro. La sesión vive en el navegador; lo que protege las operaciones es este servidor,
que exige un ID token de Firebase válido en cada llamada a /auth/me y /api/registro.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from simulator_v2.config import NODES
from simulator_v2.credentials import NodeRegistryStore
from simulator_v2.firebase_auth import (
    FirebaseVerifier, ForbiddenError, UnauthorizedError, parse_allowed_emails,
)
from simulator_v2.registro import ConsultaClient, RegistrationService, RegistroError

DEFAULT_NODE = next(iter(NODES))
PAGES = Path(__file__).resolve().parent / "paginas"
STATIC_FILES = {
    "/login": ("login/login.html", "text/html; charset=utf-8"),
    "/perfil": ("perfil/perfil.html", "text/html; charset=utf-8"),
    "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/static/js/sesion.js": ("js/sesion.js", "text/javascript; charset=utf-8"),
    "/paginas/login/login.css": ("login/login.css", "text/css; charset=utf-8"),
    "/paginas/perfil/perfil.css": ("perfil/perfil.css", "text/css; charset=utf-8"),
}

Response = tuple[int, str, bytes]


def _json(status: int, payload: Any) -> Response:
    return status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8")


@dataclass
class FirebaseSettings:
    project_id: str = ""
    api_key: str = ""
    auth_domain: str = ""
    app_id: str = ""
    messaging_sender_id: str = ""
    storage_bucket: str = ""
    admin_emails: str = ""

    @classmethod
    def from_env(cls) -> "FirebaseSettings":
        env = os.environ.get
        return cls(
            project_id=env("SENTINEL_FIREBASE_PROJECT_ID", ""),
            api_key=env("SENTINEL_FIREBASE_API_KEY", ""),
            auth_domain=env("SENTINEL_FIREBASE_AUTH_DOMAIN", ""),
            app_id=env("SENTINEL_FIREBASE_APP_ID", ""),
            messaging_sender_id=env("SENTINEL_FIREBASE_MESSAGING_SENDER_ID", ""),
            storage_bucket=env("SENTINEL_FIREBASE_STORAGE_BUCKET", ""),
            admin_emails=env("SENTINEL_FIREBASE_ADMIN_EMAILS", ""),
        )


@dataclass
class AuthWeb:
    registration: RegistrationService
    settings: FirebaseSettings = field(default_factory=FirebaseSettings)
    verifier: FirebaseVerifier | None = None

    @classmethod
    def build(cls, data_dir: Path, consulta_url: str | None = None) -> "AuthWeb":
        settings = FirebaseSettings.from_env()
        store = NodeRegistryStore(data_dir / "node_credentials.json")
        consulta = ConsultaClient(consulta_url or os.environ.get("SENTINEL_CONSULTA_URL", ""))
        verifier = None
        if settings.project_id:
            verifier = FirebaseVerifier(settings.project_id, parse_allowed_emails(settings.admin_emails))
        return cls(RegistrationService(store, consulta, tuple(NODES)), settings, verifier)

    def start_background_poll(self, interval_s: float = 5.0) -> threading.Thread:
        """Recoge el token en cuanto el administrador aprueba, sin depender de tener /perfil abierto.

        consulta entrega el token una sola vez y solo a quien pregunta con el poll_secret; si nadie
        pregunta, el nodo queda aprobado pero sin credencial y no puede enviar.
        """
        def loop() -> None:
            while True:
                for node in self.registration.nodes:
                    try:
                        request = self.registration.store.get_request(node)
                        if request and request["status"] == "pending":
                            self.registration.poll(node)
                    except Exception as exc:  # un fallo de red no debe detener el sondeo
                        print(f"registro | sondeo de {node} falló: {exc}")
                time.sleep(interval_s)

        thread = threading.Thread(target=loop, name="registro-poll", daemon=True)
        thread.start()
        return thread

    # -- autenticación ---------------------------------------------------------------------
    def _user(self, headers: Any) -> tuple[Any | None, Response | None]:
        if self.verifier is None:
            return None, _json(503, {"detail": "Firebase authentication is not configured"})
        auth = headers.get("Authorization", "")
        if not auth.lower().startswith("bearer ") or not auth[7:].strip():
            return None, _json(401, {"detail": "Missing bearer token"})
        try:
            return self.verifier.verify(auth[7:].strip()), None
        except UnauthorizedError:
            return None, _json(401, {"detail": "Invalid or expired token"})
        except ForbiddenError:
            return None, _json(403, {"detail": "User is not allowed to use this panel"})
        except Exception as exc:  # llaves públicas de Google inalcanzables
            return None, _json(503, {"detail": f"Could not reach the Firebase public key service: {exc}"})

    # -- rutas ---------------------------------------------------------------------------
    def get(self, raw_path: str, headers: Any) -> Response | None:
        url = urlparse(raw_path)
        path = url.path
        if path in STATIC_FILES:
            name, content_type = STATIC_FILES[path]
            return 200, content_type, (PAGES / name).read_bytes()
        if path == "/auth/config":
            s = self.settings
            return _json(200, {
                "configurado": bool(s.project_id and s.api_key), "apiKey": s.api_key,
                "authDomain": s.auth_domain, "projectId": s.project_id, "appId": s.app_id,
                "messagingSenderId": s.messaging_sender_id, "storageBucket": s.storage_bucket,
            })
        if path == "/auth/me":
            user, error = self._user(headers)
            return error or _json(200, {"uid": user.uid, "email": user.email,
                                        "email_verificado": user.email_verified})
        if path == "/api/registro":
            _, error = self._user(headers)
            if error:
                return error
            node = parse_qs(url.query).get("node", [DEFAULT_NODE])[0]
            return self._guarded(lambda: self.registration.poll(node))
        return None

    def post(self, raw_path: str, headers: Any, body: bytes) -> Response | None:
        url = urlparse(raw_path)
        if url.path != "/api/registro":
            return None
        _, error = self._user(headers)
        if error:
            return error
        try:
            data = json.loads(body or b"{}")
            name = str(data["name"]).strip()
            building_id, zone_id = int(data["building_id"]), int(data["zone_id"])
        except (ValueError, KeyError, TypeError):
            return _json(422, {"detail": "Se requieren name, building_id y zone_id."})
        if not 1 <= len(name) <= 150 or building_id < 1 or zone_id < 1:
            return _json(422, {"detail": "Nombre de 1 a 150 caracteres e ids mayores que 0."})
        node = parse_qs(url.query).get("node", [DEFAULT_NODE])[0]
        status, content_type, payload = self._guarded(
            lambda: self.registration.request(node, name, building_id, zone_id))
        return (202 if status == 200 else status), content_type, payload

    def _guarded(self, action: Callable[[], dict[str, Any]]) -> Response:
        try:
            return _json(200, action())
        except RegistroError as exc:
            return _json(exc.http_status, {"detail": exc.message})
