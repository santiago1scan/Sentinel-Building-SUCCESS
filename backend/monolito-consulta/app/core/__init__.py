"""Core configuration module."""
from app.core.config import settings
from app.core.database import close_db, get_db, init_db
from app.core.exceptions import (
    AppException,
    BadRequestError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    TooManyRequestsError,
    UnauthorizedError,
    UnprocessableEntityError,
)

__all__ = [
    "settings",
    "get_db",
    "init_db",
    "close_db",
    "AppException",
    "BadRequestError",
    "ConflictError",
    "DatabaseError",
    "ExternalServiceError",
    "ForbiddenError",
    "InternalServerError",
    "NotFoundError",
    "ServiceUnavailableError",
    "TooManyRequestsError",
    "UnauthorizedError",
    "UnprocessableEntityError",
]
