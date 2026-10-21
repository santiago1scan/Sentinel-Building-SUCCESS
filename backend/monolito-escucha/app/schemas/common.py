"""Common schemas for error responses."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """Error detail object."""

    code: str
    message: str
    field: str | None = None
    extra: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response format (RFC 7807 inspired)."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    status: int
    error: str
    message: str
    path: str | None = None
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


class ValidationErrorResponse(ErrorResponse):
    """422 Validation error response."""

    details: list[ErrorDetail]


def create_error_response(
    status: int,
    error: str,
    message: str,
    path: str | None = None,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> ErrorResponse:
    """Factory for creating error responses."""
    return ErrorResponse(
        timestamp=datetime.utcnow(),
        status=status,
        error=error,
        message=message,
        path=path,
        details=details,
        request_id=request_id,
    )


def create_validation_error_response(
    path: str,
    validation_errors: list[dict[str, Any]],
    request_id: str | None = None,
) -> ValidationErrorResponse:
    """Create 422 validation error response from Pydantic errors."""
    details = [
        ErrorDetail(
            code="validation_error",
            message=err.get("msg", "Validation error"),
            field=".".join(str(loc) for loc in err.get("loc", [])),
        )
        for err in validation_errors
    ]
    return ValidationErrorResponse(
        timestamp=datetime.utcnow(),
        status=422,
        error="Unprocessable Entity",
        message="Request validation failed",
        path=path,
        details=details,
        request_id=request_id,
    )
