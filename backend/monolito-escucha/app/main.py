"""Main FastAPI application."""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import (
    alerts,
    app_roles,
    app_users,
    buildings,
    connectivity_logs,
    health,
    nodes,
    readings,
    sensor_types,
    sensors,
    telemetry,
    zones,
)
from app.core.database import close_db, init_db
from app.core.exceptions import AppException
from app.core.mqtt_handler import initialize_mqtt_handler, create_async_message_handler
from app.services.mqtt_consumer_service import MQTTConsumerService
from app.schemas.common import (
    ErrorDetail,
    create_error_response,
    create_validation_error_response,
)

# Global MQTT consumer
_mqtt_consumer: MQTTConsumerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _mqtt_consumer

    # Initialize database
    await init_db()

    # Initialize MQTT handler and consumer
    try:
        mqtt_handler = await initialize_mqtt_handler()

        _mqtt_consumer = MQTTConsumerService(
            broker_host="mosquitto",
            broker_port=1883,
        )
        _mqtt_consumer.set_message_handler(create_async_message_handler(mqtt_handler))
        _mqtt_consumer.start()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"⚠️  No se pudo inicializar MQTT Consumer: {e}")

    yield

    # Cleanup
    if _mqtt_consumer:
        _mqtt_consumer.stop()

    await close_db()


app = FastAPI(
    title="Monolito Escucha",
    description="API para ingesta de lecturas y gestión de alertas",
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


# Include routers
app.include_router(health.router)
app.include_router(buildings.router)
app.include_router(zones.router)
app.include_router(nodes.router)
app.include_router(sensor_types.router)
app.include_router(sensors.router)
app.include_router(readings.router)
app.include_router(alerts.router)
app.include_router(connectivity_logs.router)
app.include_router(app_users.router)
app.include_router(app_roles.router)
app.include_router(telemetry.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Monolito Escucha",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
