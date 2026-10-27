"""API routes package."""
from app.api.routes import (
    alerts,
    app_roles,
    app_users,
    buildings,
    connectivity_logs,
    nodes,
    readings,
    sensor_types,
    sensors,
    telemetry,
    zones,
)

__all__ = [
    "buildings",
    "zones",
    "nodes",
    "sensor_types",
    "sensors",
    "readings",
    "alerts",
    "connectivity_logs",
    "app_users",
    "app_roles",
    "telemetry",
]
