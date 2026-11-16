"""Página del panel de simulación, dentro del monolito.

La sesión de Firebase vive en el navegador, así que el servidor no puede exigirla
en una navegación normal: la página comprueba la sesión del lado del cliente y
vuelve a /login si no hay usuario.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGINA_PANEL = Path(__file__).resolve().parent.parent / "paginas" / "panel.html"


@router.get("/panel", response_class=HTMLResponse)
def pagina_panel() -> str:
    return PAGINA_PANEL.read_text(encoding="utf-8")
