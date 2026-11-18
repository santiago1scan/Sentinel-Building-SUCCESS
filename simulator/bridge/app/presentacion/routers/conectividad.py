"""Estado de la conexión del bridge a la red. Público, como /health: no expone secretos."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends

from app.negocio.conectividad import ServicioConectividad
from app.presentacion.dependencias import get_conectividad

router = APIRouter()


@router.get("/api/conectividad")
async def conectividad(servicio: ServicioConectividad = Depends(get_conectividad)) -> dict[str, Any]:
    # El sondeo a REST es E/S bloqueante: va fuera del event loop.
    return await asyncio.to_thread(servicio.estado)
