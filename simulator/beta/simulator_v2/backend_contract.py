from __future__ import annotations

import json
from typing import Any


def telemetry_endpoint(base_url: str) -> str:
    """Return the ingestion endpoint from either a base URL or the full endpoint."""
    normalized = base_url.rstrip("/")
    suffix = "/telemetry/aggregate"
    return normalized if normalized.endswith(suffix) else f"{normalized}{suffix}"


def validate_backend_ack(
    status: int,
    body: str,
    expected_message_uid: str,
    expected_readings: int,
) -> tuple[bool, str]:
    """Validate the backend acknowledgement before removing a queued summary."""
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

    readings_created = response.get("readings_created")
    if not isinstance(readings_created, int) or isinstance(readings_created, bool):
        return False, f"HTTP {status}: invalid readings_created"
    if readings_created < expected_readings:
        return False, (
            f"HTTP {status}: readings_created={readings_created}, "
            f"expected_at_least={expected_readings}"
        )

    return True, f"HTTP {status}: accepted {readings_created} readings"
