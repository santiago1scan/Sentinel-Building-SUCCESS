"""Resumen corto que viaja por LoRa cuando no hay conectividad."""

from typing import Any


def construir_resumen_lora(agregado: dict[str, Any]) -> dict[str, Any]:
    emergencia = agregado["priority"] != "normal"
    return {
        "schema_version": agregado["schema_version"],
        "message_uid": agregado["message_uid"],
        "message_type": "emergency_event" if emergencia else "telemetry_summary",
        "delivery_status": "emergency" if emergencia else "offline_summary",
        "building_code": agregado["building_code"],
        "generated_at": agregado["generated_at"],
        "sequence_number": agregado["sequence_number"],
        "priority": agregado["priority"],
        "bridges": agregado["bridges"],
    }
