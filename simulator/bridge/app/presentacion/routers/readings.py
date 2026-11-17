import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from app.negocio.ingesta import ServicioIngesta
from app.presentacion.dependencias import get_ingesta
from app.presentacion.schemas import IngestOut, extraer_lecturas

router = APIRouter()


@router.post("/v1/readings", status_code=202, response_model=IngestOut)
async def recibir_lecturas(
    request: Request,
    ingesta: ServicioIngesta = Depends(get_ingesta),
):
    try:
        body = json.loads((await request.body()).decode("utf-8"))
        lecturas = extraer_lecturas(body)
        # El procesamiento usa E/S bloqueante (SQLite, REST, MQTT, LoRa): va fuera del event loop.
        return await asyncio.to_thread(ingesta.ingerir, lecturas)
    except (ValueError, KeyError) as exc:  # json.JSONDecodeError también es ValueError
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # Mantiene el servicio activo ante una falla inesperada.
        ingesta.registrar_error(repr(exc))
        raise HTTPException(status_code=500, detail="Bridge processing error") from exc
