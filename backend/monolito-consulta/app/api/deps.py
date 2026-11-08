"""API dependencies."""
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.broker_admin import BrokerAdmin
from app.core.config import settings
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
from app.services.registration_service import RegistrationService
from app.services.registration_store import RegistrationStore
from app.services.app_role_service import AppRoleService
from app.services.app_user_service import AppUserService
from app.services.building_service import BuildingService
from app.services.connectivity_log_service import ConnectivityLogService
from app.services.node_service import NodeService
from app.services.reading_service import ReadingService
from app.services.sensor_service import SensorService
from app.services.sensor_type_service import SensorTypeService
from app.services.telemetry_service import TelemetryService
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


def get_broker_admin() -> BrokerAdmin | None:
    """Cliente de administración del broker, o None si no hay cuenta configurada."""
    if not settings.mqtt_admin_username or not settings.mqtt_admin_password:
        return None
    return BrokerAdmin(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_admin_username,
        password=settings.mqtt_admin_password,
        building_code=settings.building_code,
    )


_registration_store: RegistrationStore | None = None


def get_registration_store() -> RegistrationStore:
    """Un solo almacén para todo el proceso: las solicitudes viven en memoria."""
    global _registration_store
    if _registration_store is None:
        _registration_store = RegistrationStore(ttl_seconds=settings.registration_ttl_seconds)
    return _registration_store


async def get_registration_service(
    repo: NodeRepository = Depends(get_node_repo),
    zone_repo: ZoneRepository = Depends(get_zone_repo),
) -> AsyncGenerator[RegistrationService, None]:
    yield RegistrationService(get_registration_store(), repo, zone_repo, get_broker_admin())


async def get_node_service(
    repo: NodeRepository = Depends(get_node_repo),
) -> AsyncGenerator[NodeService, None]:
    yield NodeService(repo, broker=get_broker_admin())


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
