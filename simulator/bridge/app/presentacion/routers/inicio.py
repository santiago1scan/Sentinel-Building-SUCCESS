"""Primera página del bridge: gráficas de las lecturas del nodo. Sin autenticación."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from app.negocio.graficas import MINUTOS_MAXIMOS, ServicioGraficas
from app.presentacion.componentes.graficas_svg import dibujar
from app.presentacion.dependencias import get_graficas
from app.presentacion.plantillas import plantillas

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, graficas: ServicioGraficas = Depends(get_graficas)):
    contexto = {"nodo": graficas.nodo, "graficas": graficas.nombres()}
    return plantillas.TemplateResponse(request, "inicio/inicio.html", contexto)


@router.get("/graficas/{nombre}.svg")
def grafica(
    nombre: str,
    minutos: int = Query(60, ge=1, le=MINUTOS_MAXIMOS),
    graficas: ServicioGraficas = Depends(get_graficas),
) -> Response:
    try:
        datos = graficas.datos(nombre, minutos)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=dibujar(datos), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})
