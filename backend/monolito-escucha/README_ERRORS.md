# Error Handling Documentation

## Overview

This document describes the error handling architecture implemented in the Monolito Escucha API. The system uses custom exceptions, global exception handlers, and standardized error responses following RFC 7807 (Problem Details for HTTP APIs) principles.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REQUEST                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI ROUTER                                │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Business   │  │  Database   │  │  External Services      │  │
│  │  Logic      │──│  Operations │──│  (MQTT, ThingsBoard)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         │                │                    │                  │
│         ▼                ▼                    ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              CUSTOM EXCEPTIONS                              ││
│  │  NotFoundError │ ConflictError │ ServiceUnavailableError   ││
│  │  BadRequestError │ UnauthorizedError │ ForbiddenError       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 GLOBAL EXCEPTION HANDLERS                       │
│  AppException → JSONResponse (status_code + ErrorResponse)      │
│  HTTPException → JSONResponse                                   │
│  RequestValidationError → 422 ValidationErrorResponse          │
│  IntegrityError → 409/400 Conflict/BadRequest                   │
│  SQLAlchemyError → 503 ServiceUnavailable                       │
│  Exception → 500 InternalServerError                            │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STANDARDIZED RESPONSE                         │
│  ErrorResponse / ValidationErrorResponse (RFC 7807 style)       │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
app/
├── core/
│   └── exceptions.py          # Custom exception classes
├── schemas/
│   └── common.py              # Error response schemas
├── main.py                    # Global exception handlers
└── services/
    ├── building_service.py    # Example: uses custom exceptions
    ├── zone_service.py
    └── node_service.py
```

## Exception Classes

### Base Exception

```python
# app/core/exceptions.py
class AppException(Exception):
    status_code: int = 500
    default_detail: str = "Internal server error"
    
    def __init__(self, detail: str = None, status_code: int = None, extra: dict = None):
        ...
```

### Available Exceptions

| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `BadRequestError` | 400 | Invalid request data, business rule violations |
| `UnauthorizedError` | 401 | Missing/invalid authentication |
| `ForbiddenError` | 403 | Authenticated but insufficient permissions |
| `NotFoundError` | 404 | Resource doesn't exist |
| `ConflictError` | 409 | Duplicate resource, constraint violation |
| `UnprocessableEntityError` | 422 | Semantic validation errors |
| `TooManyRequestsError` | 429 | Rate limiting |
| `InternalServerError` | 500 | Unexpected server errors |
| `ServiceUnavailableError` | 503 | Database/external service down |
| `DatabaseError` | 500 | Database operation failures |
| `ExternalServiceError` | 502 | Third-party service failures |

### Usage in Services

```python
from app.core.exceptions import NotFoundError, ConflictError, ServiceUnavailableError

class BuildingService:
    async def get(self, building_id: int) -> BuildingRead:
        building = await self.repository.get(building_id)
        if not building:
            raise NotFoundError(f"Building with id {building_id} not found")
        return BuildingRead.model_validate(building)

    async def create(self, building_in: BuildingCreate) -> BuildingRead:
        try:
            building = await self.repository.create(building_in)
        except IntegrityError as e:
            if "unique constraint" in str(e).lower():
                raise ConflictError("Building name already exists")
            raise ServiceUnavailableError("Database error")
        return BuildingRead.model_validate(building)
```

## Error Response Format

### Standard Error Response (4xx, 5xx)

```json
{
  "timestamp": "2026-10-21T03:48:12.645390",
  "status": 404,
  "error": "NotFoundError",
  "message": "Building with id 9999 not found",
  "path": "/buildings/9999",
  "details": null,
  "request_id": "f901b218"
}
```

### Validation Error Response (422)

```json
{
  "timestamp": "2026-10-21T03:48:17.016233",
  "status": 422,
  "error": "Unprocessable Entity",
  "message": "Request validation failed",
  "path": "/buildings",
  "details": [
    {
      "code": "validation_error",
      "message": "Field required",
      "field": "body.name",
      "extra": null
    }
  ],
  "request_id": "39602823"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | datetime | UTC timestamp when error occurred |
| `status` | int | HTTP status code |
| `error` | string | Exception class name |
| `message` | string | Human-readable error message |
| `path` | string | Request path that caused the error |
| `details` | array | Additional error details (for validation errors) |
| `details[].code` | string | Error code (e.g., "validation_error") |
| `details[].message` | string | Specific error message |
| `details[].field` | string | Field path that caused the error |
| `details[].extra` | object | Additional context |
| `request_id` | string | Unique request identifier for tracing |

## HTTP Status Codes Mapping

| Status Code | Exception | Description |
|-------------|-----------|-------------|
| 400 | `BadRequestError` | Invalid request payload or business rule |
| 401 | `UnauthorizedError` | Missing or invalid authentication |
| 403 | `ForbiddenError` | Insufficient permissions |
| 404 | `NotFoundError` | Resource not found |
| 409 | `ConflictError` | Duplicate resource / constraint violation |
| 422 | `RequestValidationError` | Pydantic validation failed |
| 429 | `TooManyRequestsError` | Rate limit exceeded |
| 500 | `InternalServerError` | Unexpected server error |
| 502 | `ExternalServiceError` | Upstream service error |
| 503 | `ServiceUnavailableError` | Database/service temporarily down |

## Database Error Handling

The system automatically maps common database errors:

| Database Error | HTTP Status | Mapped Exception |
|----------------|-------------|------------------|
| Unique constraint violation | 409 | `ConflictError` |
| Foreign key violation | 400 | `BadRequestError` |
| Other integrity errors | 409 | `ConflictError` |
| Connection/timeout errors | 503 | `ServiceUnavailableError` |
| Other SQLAlchemy errors | 503 | `ServiceUnavailableError` |

## Request ID Tracking

Each error response includes a `request_id` for debugging:

- Generated from `X-Request-ID` header if present
- Auto-generated UUID (8 chars) if not provided
- Include in logs for traceability

```bash
# Client sends request ID
curl -H "X-Request-ID: abc-123" http://localhost:8089/buildings/9999
```

Response:
```json
{
  "request_id": "abc-123",
  ...
}
```

## Testing Error Responses

```bash
# 404 Not Found
curl http://localhost:8089/buildings/9999

# 422 Validation Error
curl -X POST http://localhost:8089/buildings -H "Content-Type: application/json" -d '{"address":"Test"}'

# 404 on DELETE
curl -X DELETE http://localhost:8089/buildings/9999

# 422 on invalid data types
curl -X POST http://localhost:8089/buildings -H "Content-Type: application/json" -d '{"name":123,"address":"Test"}'
```

## Adding New Exceptions

1. **Create exception class** in `app/core/exceptions.py`:
```python
class CustomBusinessError(AppException):
    status_code = 422
    default_detail = "Business rule violation"
```

2. **Use in service**:
```python
raise CustomBusinessError("Specific business rule violated")
```

3. **No handler needed** - automatically handled by `app_exception_handler`

## Best Practices

1. **Use specific exceptions** - Don't use generic `AppException`, use `NotFoundError`, `ConflictError`, etc.

2. **Include context** - Use `extra` parameter for additional debugging info:
```python
raise ConflictError("Email already registered", extra={"email": "user@example.com"})
```

3. **Don't expose internals** - Error messages should be user-friendly, not stack traces

4. **Log server errors** - 5xx errors are logged automatically via `global_exception_handler`

5. **Validate early** - Use Pydantic models for request validation (automatic 422)

6. **Handle at service layer** - Let services raise exceptions, routers stay clean

## Example: Complete Flow

```python
# 1. Router (clean - no try/except)
@router.get("/{building_id}", response_model=BuildingRead)
async def get_building(building_id: int, service: BuildingService = Depends(...)):
    return await service.get(building_id)

# 2. Service (business logic + exceptions)
async def get(self, building_id: int) -> BuildingRead:
    building = await self.repository.get(building_id)
    if not building:
        raise NotFoundError(f"Building {building_id} not found")
    return BuildingRead.model_validate(building)

# 3. Handler (automatic)
# NotFoundError → 404 + ErrorResponse
```

## Extending for Authentication

When adding auth, add these exceptions:

```python
class InvalidTokenError(UnauthorizedError):
    default_detail = "Invalid or expired token"

class InsufficientScopeError(ForbiddenError):
    default_detail = "Insufficient permissions for this operation"
```

And in dependencies:
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    if not token:
        raise UnauthorizedError("Missing authentication token")
    user = await verify_token(token)
    if not user:
        raise InvalidTokenError()
    return user
```