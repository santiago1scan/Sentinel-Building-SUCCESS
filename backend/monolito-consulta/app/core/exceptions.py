"""Custom application exceptions."""
from typing import Any


class AppException(Exception):
    """Base application exception."""

    status_code: int = 500
    default_detail: str = "Internal server error"

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.detail = detail or self.default_detail
        if status_code:
            self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.detail)


class BadRequestError(AppException):
    """400 Bad Request - Invalid request data or business rule violation."""

    status_code = 400
    default_detail = "Bad request"


class UnauthorizedError(AppException):
    """401 Unauthorized - Authentication required or invalid."""

    status_code = 401
    default_detail = "Unauthorized"


class ForbiddenError(AppException):
    """403 Forbidden - Authenticated but insufficient permissions."""

    status_code = 403
    default_detail = "Forbidden"


class NotFoundError(AppException):
    """404 Not Found - Resource does not exist."""

    status_code = 404
    default_detail = "Resource not found"


class ConflictError(AppException):
    """409 Conflict - Resource already exists or constraint violation."""

    status_code = 409
    default_detail = "Conflict"


class UnprocessableEntityError(AppException):
    """422 Unprocessable Entity - Semantic errors in request."""

    status_code = 422
    default_detail = "Unprocessable entity"


class TooManyRequestsError(AppException):
    """429 Too Many Requests - Rate limit exceeded."""

    status_code = 429
    default_detail = "Rate limit exceeded"


class InternalServerError(AppException):
    """500 Internal Server Error - Unexpected server error."""

    status_code = 500
    default_detail = "Internal server error"


class ServiceUnavailableError(AppException):
    """503 Service Unavailable - Service temporarily unavailable."""

    status_code = 503
    default_detail = "Service temporarily unavailable"


class DatabaseError(AppException):
    """Database operation error."""

    status_code = 500
    default_detail = "Database error"


class ExternalServiceError(AppException):
    """External service integration error."""

    status_code = 502
    default_detail = "External service error"
