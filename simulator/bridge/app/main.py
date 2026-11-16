from fastapi import FastAPI

from app.presentacion.routers import health

app = FastAPI(title="Sentinel bridge (monolito)")
app.include_router(health.router)
