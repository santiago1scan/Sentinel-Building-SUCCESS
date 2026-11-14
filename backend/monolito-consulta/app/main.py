"""Main FastAPI application - Data Management & CRUD."""
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import require_user
from app.api.routes import (
    alerts,
    app_roles,
    app_users,
    buildings,
    connectivity_logs,
    health,
    nodes,
    readings,
    registrations,
    sensor_types,
    sensors,
    zones,
)
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppException
from app.schemas.common import (
    ErrorDetail,
    create_error_response,
    create_validation_error_response,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Initialize database
    await init_db()

    yield

    await close_db()


app = FastAPI(
    title="Monolito Consulta",
    description="Data Management & CRUD Operations",
    version="0.1.0",
    lifespan=lifespan,
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_response = create_error_response(
        status=exc.status_code,
        error=exc.__class__.__name__,
        message=exc.detail,
        path=str(request.url.path),
        request_id=request_id,
    )
    if exc.extra:
        error_response.details = [
            ErrorDetail(
                code="server_error",
                message=exc.detail,
                extra=exc.extra,
            )
        ]
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTP exceptions."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_response = create_error_response(
        status=exc.status_code,
        error="HTTPException",
        message=exc.detail,
        path=str(request.url.path),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors (422)."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_response = create_validation_error_response(
        path=str(request.url.path),
        validation_errors=exc.errors(),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity errors (unique constraint, FK violation)."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_msg = str(exc.orig) if exc.orig else "Database integrity error"

    if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
        status_code = status.HTTP_409_CONFLICT
        error = "ConflictError"
        message = "Resource already exists"
    elif "foreign key" in error_msg.lower():
        status_code = status.HTTP_400_BAD_REQUEST
        error = "BadRequestError"
        message = "Invalid reference to related resource"
    else:
        status_code = status.HTTP_409_CONFLICT
        error = "ConflictError"
        message = "Database constraint violation"

    error_response = create_error_response(
        status=status_code,
        error=error,
        message=message,
        path=str(request.url.path),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle general SQLAlchemy errors."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_response = create_error_response(
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        error="ServiceUnavailableError",
        message="Database temporarily unavailable",
        path=str(request.url.path),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions (500)."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    error_response = create_error_response(
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="InternalServerError",
        message="An unexpected error occurred",
        path=str(request.url.path),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


# Include routers (CRUD only, no MQTT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    # CORS abierto: cualquier método y header (Authorization, X-Poll-Secret, ...). La autenticación va
    # en el header Bearer, no en cookies, así que no se habilitan credenciales.
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Rutas de administración: exigen el ID token de Firebase del panel.
_protected = [Depends(require_user)]
app.include_router(buildings.router, dependencies=_protected)
app.include_router(zones.router, dependencies=_protected)
app.include_router(nodes.router, dependencies=_protected)
# registrations mezcla rutas del bridge (abiertas, con X-Poll-Secret) y del administrador:
# la protección va por ruta, dentro del router.
app.include_router(registrations.router)
app.include_router(sensor_types.router, dependencies=_protected)
app.include_router(sensors.router, dependencies=_protected)
app.include_router(readings.router, dependencies=_protected)
app.include_router(alerts.router, dependencies=_protected)
app.include_router(connectivity_logs.router, dependencies=_protected)
app.include_router(app_users.router, dependencies=_protected)
app.include_router(app_roles.router, dependencies=_protected)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Monolito Consulta",
        "description": "Data Management & CRUD Operations",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
