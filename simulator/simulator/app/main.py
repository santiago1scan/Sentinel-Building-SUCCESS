from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings
from app.core.contenedor import crear_contenedor
from app.presentacion.routers import api, fallos, panel

ESTATICOS = Path(__file__).resolve().parent / "presentacion" / "estaticos"


def crear_app(ajustes: Settings | None = None) -> FastAPI:
    config = ajustes or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.contenedor = crear_contenedor(config)
        if config.autostart:
            app.state.contenedor.controlador.iniciar()
        try:
            yield
        finally:
            # Al cerrar el servicio se limpian las anomalías y se detiene el ciclo.
            app.state.contenedor.controlador.apagar()

    app = FastAPI(title="Sentinel simulador de sensores", lifespan=lifespan)
    app.include_router(panel.router)
    app.include_router(api.router)
    app.include_router(fallos.router)
    app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")
    return app


app = crear_app()
