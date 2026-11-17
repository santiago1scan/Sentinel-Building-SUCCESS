"""Fallos y anomalías manuales: lo que antes eran comandos de consola del simulador."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.negocio.simulacion import ControladorSimulacion
from app.presentacion.dependencias import get_controlador

router = APIRouter(prefix="/api/fallos", tags=["fallos"])


def _ejecutar(accion, *args) -> JSONResponse:
    try:
        return JSONResponse(accion(*args))
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)


@router.get("")
def estado_fallos(controlador: ControladorSimulacion = Depends(get_controlador)):
    return controlador.fallos()


@router.post("/nodo/{nodo}/apagar")
def apagar_nodo(nodo: str, controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.apagar_nodo, nodo)


@router.post("/nodo/{nodo}/encender")
def encender_nodo(nodo: str, controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.encender_nodo, nodo)


@router.post("/sensor/{nodo}/{sensor}/silenciar")
def silenciar_sensor(nodo: str, sensor: str,
                     controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.silenciar_sensor, nodo, sensor)


@router.post("/sensor/{nodo}/{sensor}/reactivar")
def reactivar_sensor(nodo: str, sensor: str,
                     controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.reactivar_sensor, nodo, sensor)


@router.post("/anomalia/{nodo}/{sensor}")
def poner_anomalia(nodo: str, sensor: str,
                   controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.poner_anomalia, nodo, sensor)


@router.delete("/anomalia/{nodo}/{sensor}")
def limpiar_anomalia(nodo: str, sensor: str,
                     controlador: ControladorSimulacion = Depends(get_controlador)):
    return _ejecutar(controlador.limpiar_anomalia, nodo, sensor)
