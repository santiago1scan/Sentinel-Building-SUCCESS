"""Models package - exports all models for Alembic autogenerate."""
from app.models.alert import Alert
from app.models.app_role import AppRole
from app.models.app_user import AppUser
from app.models.base import Base
from app.models.building import Building
from app.models.connectivity_log import ConnectivityLog
from app.models.node import Node
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.models.sensor_type import SensorType
from app.models.zone import Zone

metadata = Base.metadata

__all__ = [
    "Base",
    "metadata",
    "AppRole",
    "AppUser",
    "Alert",
    "Building",
    "ConnectivityLog",
    "Node",
    "Reading",
    "Sensor",
    "SensorType",
    "Zone",
]
