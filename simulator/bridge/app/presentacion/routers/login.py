"""Página de inicio de sesión y verificación de la sesión de Firebase."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.core.firebase_auth import FirebaseUser
from app.presentacion.auth import require_user

router = APIRouter()

PAGINA_LOGIN = Path(__file__).resolve().parent.parent / "paginas" / "login.html"


@router.get("/login", response_class=HTMLResponse)
def pagina_login() -> str:
    return PAGINA_LOGIN.read_text(encoding="utf-8")


@router.get("/auth/config")
def configuracion_publica() -> dict[str, Any]:
    """Valores públicos del proyecto Firebase para el SDK del navegador (no incluye secretos)."""
    ajustes = get_settings()
    return {
        "configurado": bool(ajustes.firebase_project_id and ajustes.firebase_api_key),
        "apiKey": ajustes.firebase_api_key,
        "authDomain": ajustes.firebase_auth_domain,
        "projectId": ajustes.firebase_project_id,
        "appId": ajustes.firebase_app_id,
        "messagingSenderId": ajustes.firebase_messaging_sender_id,
        "storageBucket": ajustes.firebase_storage_bucket,
        "panelUrl": ajustes.panel_url,
    }


@router.get("/auth/me")
def sesion_actual(user: FirebaseUser = Depends(require_user)) -> dict[str, Any]:
    return {"uid": user.uid, "email": user.email, "email_verificado": user.email_verified}
