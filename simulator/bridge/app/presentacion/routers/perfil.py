"""Página de perfil y API del registro del nodo.

La sesión de Firebase vive en el navegador, así que la página se protege allí (sin sesión
vuelve a /login). Lo que de verdad protege las operaciones es el servidor: la API del
registro exige un ID token de Firebase válido (`require_user`).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.firebase_auth import FirebaseUser
from app.negocio.registro_nodo import RegistroError, ServicioRegistro
from app.presentacion.auth import require_user
from app.presentacion.dependencias import get_registro
from app.presentacion.plantillas import plantillas
from app.presentacion.schemas import RegistroIn

router = APIRouter()


@router.get("/perfil", response_class=HTMLResponse)
def pagina_perfil(request: Request):
    return plantillas.TemplateResponse(request, "perfil/perfil.html")


@router.get("/api/registro")
def estado_registro(
    _usuario: FirebaseUser = Depends(require_user),
    registro: ServicioRegistro = Depends(get_registro),
) -> dict[str, Any]:
    """Estado del registro. Si hay una solicitud pendiente, consulta a consulta y aplica el token."""
    return registro.consultar()


@router.post("/api/registro", status_code=202)
def solicitar_registro(
    cuerpo: RegistroIn,
    _usuario: FirebaseUser = Depends(require_user),
    registro: ServicioRegistro = Depends(get_registro),
) -> dict[str, Any]:
    try:
        return registro.solicitar(cuerpo.name.strip(), cuerpo.building_id, cuerpo.zone_id)
    except RegistroError as exc:
        raise HTTPException(status_code=exc.estado_http, detail=exc.mensaje) from exc
