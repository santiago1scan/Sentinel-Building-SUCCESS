"""API dependencies."""
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.alert_repository import AlertRepository
from app.repositories.app_role_repository import AppRoleRepository
from app.repositories.app_user_repository import AppUserRepository
from app.repositories.building_repository import BuildingRepository
from app.repositories.connectivity_log_repository import ConnectivityLogRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.zone_repository import ZoneRepository
from app.services.alert_service import AlertService
from app.services.app_role_service import AppRoleService
from app.services.app_user_service import AppUserService
from app.services.building_service import BuildingService
from app.services.connectivity_log_service import ConnectivityLogService
from app.services.node_service import NodeService
from app.services.reading_service import ReadingService
from app.services.sensor_service import SensorService
from app.services.sensor_type_service import SensorTypeService
from app.services.zone_service import ZoneService


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


async def get_alert_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AlertRepository, None]:
    yield AlertRepository(db)


async def get_connectivity_log_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[ConnectivityLogRepository, None]:
    yield ConnectivityLogRepository(db)


async def get_app_user_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AppUserRepository, None]:
    yield AppUserRepository(db)


async def get_app_role_repo(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AppRoleRepository, None]:
    yield AppRoleRepository(db)


# Service dependencies
async def get_building_service(
    repo: BuildingRepository = Depends(get_building_repo),
) -> AsyncGenerator[BuildingService, None]:
    yield BuildingService(repo)


async def get_zone_service(
    repo: ZoneRepository = Depends(get_zone_repo),
) -> AsyncGenerator[ZoneService, None]:
    yield ZoneService(repo)


async def get_node_service(
    repo: NodeRepository = Depends(get_node_repo),
) -> AsyncGenerator[NodeService, None]:
    yield NodeService(repo)


async def get_sensor_type_service(
    repo: SensorTypeRepository = Depends(get_sensor_type_repo),
) -> AsyncGenerator[SensorTypeService, None]:
    yield SensorTypeService(repo)


async def get_sensor_service(
    repo: SensorRepository = Depends(get_sensor_repo),
) -> AsyncGenerator[SensorService, None]:
    yield SensorService(repo)


async def get_reading_service(
    repo: ReadingRepository = Depends(get_reading_repo),
) -> AsyncGenerator[ReadingService, None]:
    yield ReadingService(repo)


async def get_alert_service(
    repo: AlertRepository = Depends(get_alert_repo),
) -> AsyncGenerator[AlertService, None]:
    yield AlertService(repo)


async def get_connectivity_log_service(
    repo: ConnectivityLogRepository = Depends(get_connectivity_log_repo),
) -> AsyncGenerator[ConnectivityLogService, None]:
    yield ConnectivityLogService(repo)


async def get_app_user_service(
    repo: AppUserRepository = Depends(get_app_user_repo),
) -> AsyncGenerator[AppUserService, None]:
    yield AppUserService(repo)


async def get_app_role_service(
    repo: AppRoleRepository = Depends(get_app_role_repo),
) -> AsyncGenerator[AppRoleService, None]:
    yield AppRoleService(repo)
