from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.contenedor import crear_contenedor
from app.presentacion.routers import health, login, readings


def crear_app(ajustes: Settings | None = None) -> FastAPI:
    config = ajustes or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.contenedor = crear_contenedor(config)
        try:
            yield
        finally:
            app.state.contenedor.cerrar()

    app = FastAPI(title="Sentinel bridge (monolito)", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(readings.router)
    app.include_router(login.router)
    return app


app = crear_app()
