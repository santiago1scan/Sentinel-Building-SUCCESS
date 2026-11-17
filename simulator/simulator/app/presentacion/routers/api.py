"""API del panel de escenarios. Mismo contrato que scenario_server.py, para que el panel no cambie."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.negocio.simulacion import ControladorSimulacion
from app.presentacion.dependencias import get_controlador

router = APIRouter(prefix="/api")

LIMITE_CUERPO = 64 * 1024


async def leer_json(request: Request) -> dict[str, Any]:
    cuerpo = await request.body()
    if len(cuerpo) > LIMITE_CUERPO:
        raise ValueError("Request body must be no larger than 64 KiB.")
    if not cuerpo:
        return {}
    try:
        valor = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must contain valid UTF-8 JSON.") from exc
    if not isinstance(valor, dict):
        raise ValueError("Request JSON must be an object.")
    return valor


def responder(resultado: dict[str, Any]) -> JSONResponse:
    return JSONResponse(resultado, status_code=200 if resultado.get("ok") else 400)


def error_400(exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


@router.get("/status")
async def estado(controlador: ControladorSimulacion = Depends(get_controlador)):
    # Consulta el /health del bridge (E/S bloqueante): fuera del event loop.
    return await asyncio.to_thread(controlador.estado_panel)


@router.post("/simulator/start")
async def iniciar_simulador(request: Request,
                            controlador: ControladorSimulacion = Depends(get_controlador)):
    try:
        await leer_json(request)
    except ValueError as exc:
        return error_400(exc)
    return responder(controlador.iniciar())


@router.post("/simulator/stop")
async def detener_simulador(request: Request,
                            controlador: ControladorSimulacion = Depends(get_controlador)):
    try:
        await leer_json(request)
    except ValueError as exc:
        return error_400(exc)
    return responder(await asyncio.to_thread(controlador.detener))


@router.post("/scenario/start")
async def iniciar_escenario(request: Request,
                            controlador: ControladorSimulacion = Depends(get_controlador)):
    try:
        cuerpo = await leer_json(request)
        resultado = controlador.iniciar_escenario_desde(cuerpo)
    except ValueError as exc:
        return error_400(exc)
    return responder(resultado)


@router.post("/scenario/stop")
async def detener_escenario(request: Request,
                            controlador: ControladorSimulacion = Depends(get_controlador)):
    try:
        await leer_json(request)
    except ValueError as exc:
        return error_400(exc)
    return responder(controlador.detener_escenario())
