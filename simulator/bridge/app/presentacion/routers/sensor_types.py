"""Catálogo de tipos de sensor y sus métricas, tomado de consulta.

Exige sesión de Firebase (igual que consulta) y reenvía el token del usuario.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.firebase_auth import FirebaseUser
from app.negocio.catalogo_sensores import CatalogoError, ServicioCatalogoSensores
from app.presentacion.auth import get_token, require_user
from app.presentacion.dependencias import get_catalogo_sensores

router = APIRouter(prefix="/sensor-types", tags=["sensor-types"])


@router.get("")
def listar_tipos_sensor(
    _usuario: FirebaseUser = Depends(require_user),
    token: str = Depends(get_token),
    catalogo: ServicioCatalogoSensores = Depends(get_catalogo_sensores),
) -> list[dict[str, Any]]:
    try:
        return catalogo.listar(token)
    except CatalogoError as exc:
        raise HTTPException(status_code=exc.estado_http, detail=exc.mensaje) from exc


@router.get("/{sensor_type_id}")
def obtener_tipo_sensor(
    sensor_type_id: int,
    _usuario: FirebaseUser = Depends(require_user),
    token: str = Depends(get_token),
    catalogo: ServicioCatalogoSensores = Depends(get_catalogo_sensores),
) -> dict[str, Any]:
    try:
        return catalogo.obtener(sensor_type_id, token)
    except CatalogoError as exc:
        raise HTTPException(status_code=exc.estado_http, detail=exc.mensaje) from exc
