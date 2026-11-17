"""Dependencia de autenticación: exige un ID token de Firebase en `Authorization: Bearer`.

Mismo comportamiento que monolito-consulta/app/api/auth.py: cerrado por omisión
(sin FIREBASE_PROJECT_ID responde 503), 401 si falta o no es válido, 403 si el
usuario no está en FIREBASE_ADMIN_EMAILS.
"""

import asyncio
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errores import ForbiddenError, UnauthorizedError
from app.core.firebase_auth import FirebaseUser, FirebaseVerifier, parse_allowed_emails

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_firebase_verifier() -> FirebaseVerifier | None:
    ajustes = get_settings()
    if not ajustes.firebase_project_id:
        return None
    return FirebaseVerifier(
        project_id=ajustes.firebase_project_id,
        allowed_emails=parse_allowed_emails(ajustes.firebase_admin_emails),
    )


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> FirebaseUser:
    verifier = get_firebase_verifier()
    if verifier is None:
        raise HTTPException(status_code=503, detail="Firebase authentication is not configured")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return await asyncio.to_thread(verifier.verify, credentials.credentials)
    except UnauthorizedError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail="User is not allowed to use this panel") from exc
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(status_code=503, detail="Could not reach the Firebase public key service") from exc
