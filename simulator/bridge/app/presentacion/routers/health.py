from typing import Any

from fastapi import APIRouter, Depends

from app.negocio.ingesta import ServicioIngesta
from app.presentacion.dependencias import get_ingesta
from app.presentacion.schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health(ingesta: ServicioIngesta = Depends(get_ingesta)) -> dict[str, Any]:
    return ingesta.salud()
