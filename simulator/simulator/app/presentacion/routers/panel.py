"""Página del panel de simulación."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGINA_PANEL = Path(__file__).resolve().parent.parent / "paginas" / "panel.html"


@router.get("/", response_class=HTMLResponse)
@router.get("/panel", response_class=HTMLResponse)
def pagina_panel() -> str:
    return PAGINA_PANEL.read_text(encoding="utf-8")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "component": "simulator"}
