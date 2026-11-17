from fastapi import Request

from app.negocio.graficas import ServicioGraficas
from app.negocio.ingesta import ServicioIngesta
from app.negocio.registro_nodo import ServicioRegistro


def get_ingesta(request: Request) -> ServicioIngesta:
    return request.app.state.contenedor.ingesta


def get_graficas(request: Request) -> ServicioGraficas:
    return request.app.state.contenedor.graficas


def get_registro(request: Request) -> ServicioRegistro:
    return request.app.state.contenedor.registro
