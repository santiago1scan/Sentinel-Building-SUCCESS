"""API dependencies."""
from collections.abc import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.models.node import Node
from app.repositories.building_repository import BuildingRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.zone_repository import ZoneRepository
from app.services.node_auth_service import NodeAuthService
from app.services.telemetry_service import TelemetryService

__all__ = ["get_db", "get_telemetry_service", "get_authenticated_node"]


# Repository dependencies
async def get_building_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[BuildingRepository, None]:
    yield BuildingRepository(db)


async def get_zone_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[ZoneRepository, None]:
    yield ZoneRepository(db)


async def get_node_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[NodeRepository, None]:
    yield NodeRepository(db)


async def get_sensor_type_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SensorTypeRepository, None]:
    yield SensorTypeRepository(db)


async def get_sensor_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SensorRepository, None]:
    yield SensorRepository(db)


async def get_reading_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[ReadingRepository, None]:
    yield ReadingRepository(db)


# Service dependencies
async def get_node_auth_service(
    node_repo: NodeRepository = Depends(get_node_repo),
) -> AsyncGenerator[NodeAuthService, None]:
    yield NodeAuthService(node_repo)


async def get_authenticated_node(
    x_node_token: str | None = Header(default=None, alias="X-Node-Token"),
    auth_service: NodeAuthService = Depends(get_node_auth_service),
) -> Node:
    """Resolve the node that sent the request from its X-Node-Token header."""
    if not x_node_token:
        raise UnauthorizedError("Missing X-Node-Token header")
    return await auth_service.authenticate(x_node_token)


async def get_telemetry_service(
    building_repo: BuildingRepository = Depends(get_building_repo),
    zone_repo: ZoneRepository = Depends(get_zone_repo),
    node_repo: NodeRepository = Depends(get_node_repo),
    sensor_repo: SensorRepository = Depends(get_sensor_repo),
    sensor_type_repo: SensorTypeRepository = Depends(get_sensor_type_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
) -> AsyncGenerator[TelemetryService, None]:
    yield TelemetryService(
        building_repo,
        zone_repo,
        node_repo,
        sensor_repo,
        sensor_type_repo,
        reading_repo,
    )
