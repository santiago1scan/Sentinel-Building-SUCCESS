from __future__ import annotations

import json
from typing import Any


def telemetry_endpoint(base_url: str) -> str:
    """Acepta la URL base o el endpoint completo que me entregue el backend."""
    normalized = base_url.rstrip("/")
    suffix = "/telemetry/aggregate"
    return normalized if normalized.endswith(suffix) else f"{normalized}{suffix}"


def validate_backend_ack(
    status: int,
    body: str,
    expected_message_uid: str,
    expected_readings: int,
) -> tuple[bool, str]:
    """Solo retiro la cola cuando el backend confirma el mismo mensaje."""
    if not 200 <= status < 300:
        return False, f"HTTP {status}: {body[:2000]}"

    try:
        response: Any = json.loads(body)
    except json.JSONDecodeError:
        return False, f"HTTP {status}: invalid JSON acknowledgement"

    if not isinstance(response, dict):
        return False, f"HTTP {status}: acknowledgement must be an object"
    if response.get("message_uid") != expected_message_uid:
        return False, f"HTTP {status}: message_uid mismatch"

    errors = response.get("errors")
    if not isinstance(errors, list):
        return False, f"HTTP {status}: missing errors list"
    if errors:
        return False, f"HTTP {status}: backend errors={errors}"

    # Si la primera respuesta se perdió, el reintento llega como duplicado. El
    # backend ya conserva ese UID y por eso también puedo cerrar el pendiente.
    if response.get("duplicate") is True:
        return True, f"HTTP {status}: message already stored"

    readings_created = response.get("readings_created")
    if not isinstance(readings_created, int) or isinstance(readings_created, bool):
        return False, f"HTTP {status}: invalid readings_created"
    if readings_created < expected_readings:
        return False, (
            f"HTTP {status}: readings_created={readings_created}, "
            f"expected_at_least={expected_readings}"
        )

    return True, f"HTTP {status}: accepted {readings_created} readings"
