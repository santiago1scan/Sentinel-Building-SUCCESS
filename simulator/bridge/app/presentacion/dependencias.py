from fastapi import Request

from app.negocio.ingesta import ServicioIngesta


def get_ingesta(request: Request) -> ServicioIngesta:
    return request.app.state.contenedor.ingesta
