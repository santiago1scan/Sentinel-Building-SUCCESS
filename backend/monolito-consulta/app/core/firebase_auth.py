"""Verificación de ID tokens de Firebase Authentication (el panel web envía `Authorization: Bearer`).

Un ID token es un JWT firmado con RS256 por Google. Se acepta solo si:
- la firma corresponde a una llave pública vigente de Google (se descargan y se guardan en caché),
- `aud` es el id del proyecto y `iss` es `https://securetoken.google.com/<proyecto>`,
- no ha expirado y trae `sub` (el uid del usuario).

Opcionalmente se limita a una lista de correos (`FIREBASE_ADMIN_EMAILS`): sin esa lista, cualquier
usuario que Firebase autentique entra, y si el registro de usuarios está abierto en Firebase,
cualquiera podría crearse una cuenta.
"""
import logging
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.core.exceptions import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)

JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
ISSUER_PREFIX = "https://securetoken.google.com/"
ALGORITHMS = ["RS256"]
# Tolerancia al desfase de reloj entre este servidor y Google, en segundos.
CLOCK_SKEW_SECONDS = 10


@dataclass(frozen=True)
class FirebaseUser:
    uid: str
    email: str | None
    email_verified: bool


def parse_allowed_emails(spec: str | None) -> frozenset[str]:
    """'a@x.com, B@y.com' -> {'a@x.com', 'b@y.com'}. Sin distinguir mayúsculas."""
    return frozenset(item.strip().lower() for item in (spec or "").split(",") if item.strip())


class FirebaseVerifier:
    def __init__(
        self,
        project_id: str,
        allowed_emails: frozenset[str] = frozenset(),
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self.project_id = project_id
        self.allowed_emails = allowed_emails
        # PyJWKClient guarda en caché las llaves por `kid` y las vuelve a pedir si aparece una nueva.
        self.jwks_client = jwks_client or PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)

    def verify(self, token: str) -> FirebaseUser:
        """Valida el token. Es síncrono (puede descargar llaves): llamar con asyncio.to_thread."""
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=ALGORITHMS,
                audience=self.project_id,
                issuer=f"{ISSUER_PREFIX}{self.project_id}",
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iat", "aud", "iss", "sub"]},
            )
        except jwt.PyJWKClientConnectionError as exc:
            # No es culpa del token: no se pudieron descargar las llaves de Google.
            logger.error("No se pudieron obtener las llaves públicas de Firebase: %s", exc)
            raise
        except jwt.PyJWTError as exc:
            # El token no se registra, solo el motivo del rechazo.
            logger.warning("Token de Firebase rechazado: %s", exc)
            raise UnauthorizedError("Invalid or expired token") from exc

        uid = claims.get("sub")
        if not isinstance(uid, str) or not uid:
            logger.warning("Token de Firebase rechazado: sub vacío")
            raise UnauthorizedError("Invalid or expired token")

        email = claims.get("email")
        if self.allowed_emails and (not email or email.lower() not in self.allowed_emails):
            logger.warning("Usuario de Firebase autenticado pero no autorizado: uid=%s", uid)
            raise ForbiddenError("User is not allowed to use this panel")

        return FirebaseUser(uid=uid, email=email, email_verified=bool(claims.get("email_verified")))
