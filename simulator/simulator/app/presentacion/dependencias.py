from fastapi import Request

from app.negocio.simulacion import ControladorSimulacion


def get_controlador(request: Request) -> ControladorSimulacion:
    return request.app.state.contenedor.controlador
