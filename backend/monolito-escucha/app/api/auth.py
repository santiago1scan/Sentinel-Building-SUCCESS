"""Dependencias de autenticación del panel: el frontend envía el ID token de Firebase.

Mismo mecanismo que monolito-consulta. Aquí solo protege el stream de alertas (`/alerts/stream`);
los endpoints del nodo siguen usando X-Node-Token.
"""
import asyncio
from functools import lru_cache

import jwt
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.core.firebase_auth import FirebaseUser, FirebaseVerifier, parse_allowed_emails

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_firebase_verifier() -> FirebaseVerifier | None:
    """Un verificador por proceso (guarda en caché las llaves de Google). None si no está configurado."""
    if not settings.firebase_project_id:
        return None
    return FirebaseVerifier(
        project_id=settings.firebase_project_id,
        allowed_emails=parse_allowed_emails(settings.firebase_admin_emails),
    )


async def _authenticate(token: str | None) -> FirebaseUser:
    verifier = get_firebase_verifier()
    if verifier is None:
        # Cerrado por omisión: sin configuración, el stream no queda abierto.
        raise ServiceUnavailableError("Firebase authentication is not configured")
    if not token:
        raise UnauthorizedError("Missing bearer token")
    try:
        return await asyncio.to_thread(verifier.verify, token)
    except jwt.PyJWKClientConnectionError as exc:
        raise ServiceUnavailableError("Could not reach the Firebase public key service") from exc


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> FirebaseUser:
    """Exige `Authorization: Bearer <ID token de Firebase>` válido."""
    return await _authenticate(credentials.credentials if credentials else None)


async def require_user_or_query_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    access_token: str | None = Query(None, description="ID token; solo para EventSource, que no envía headers"),
) -> FirebaseUser:
    """Exige ID token de Firebase en `Authorization: Bearer`, o en `?access_token=` para EventSource."""
    token = credentials.credentials if credentials else access_token
    return await _authenticate(token)
