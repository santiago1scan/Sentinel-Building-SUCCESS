"""MQTT Message Handler - Process incoming telemetry messages."""
import asyncio
import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.services.telemetry_service import TelemetryService
from app.repositories.building_repository import BuildingRepository
from app.repositories.zone_repository import ZoneRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.reading_repository import ReadingRepository
from app.services.DTOS.telemetry_dto import TelemetryAggregateDTO
from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTMessageHandler:
    """Handler for processing MQTT telemetry messages."""

    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.AsyncSessionLocal = sessionmaker(
            self.db_engine, class_=AsyncSession, expire_on_commit=False
        )
        self.message_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _worker_loop(self):
        """Process messages from queue sequentially."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                telemetry = self.message_queue.get(timeout=1)
                if telemetry is None:
                    break
                loop.run_until_complete(self._process_message(telemetry))
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Error en worker thread: {e}")

    async def _process_message(self, telemetry: TelemetryAggregateDTO) -> None:
        """Internal method to process telemetry."""
        try:
            logger.info(f"🔄 Procesando telemetría: {telemetry.message_uid}")

            async with self.AsyncSessionLocal() as session:
                building_repo = BuildingRepository(session)
                zone_repo = ZoneRepository(session)
                node_repo = NodeRepository(session)
                sensor_repo = SensorRepository(session)
                sensor_type_repo = SensorTypeRepository(session)
                reading_repo = ReadingRepository(session)
                telemetry_service = TelemetryService(
                    building_repo,
                    zone_repo,
                    node_repo,
                    sensor_repo,
                    sensor_type_repo,
                    reading_repo,
                )

                result = await telemetry_service.process_telemetry(telemetry)
                logger.info(f"✅ Telemetría procesada: {result['readings_created']} lecturas creadas")

                if result["errors"]:
                    logger.warning(f"⚠️  Errores: {result['errors']}")

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")

    async def handle_message(self, telemetry: TelemetryAggregateDTO) -> None:
        """Queue message for processing."""
        self.message_queue.put(telemetry)


# Global handler instance
_mqtt_handler: MQTTMessageHandler | None = None
_event_loop = None


async def initialize_mqtt_handler() -> MQTTMessageHandler:
    """Initialize MQTT message handler with database engine."""
    global _mqtt_handler

    try:
        db_engine = create_async_engine(settings.database_url, echo=False)
        _mqtt_handler = MQTTMessageHandler(db_engine)
        logger.info("✅ MQTT Handler inicializado")
        return _mqtt_handler
    except Exception as e:
        logger.error(f"❌ Error inicializando MQTT Handler: {e}")
        raise


def get_mqtt_handler() -> MQTTMessageHandler | None:
    """Get the global MQTT handler instance."""
    return _mqtt_handler


def create_async_message_handler(handler: MQTTMessageHandler):
    """Create a sync wrapper for the async message handler."""
    import asyncio

    def sync_handler(telemetry: TelemetryAggregateDTO) -> None:
        """Sync wrapper to call async handler."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handler.handle_message(telemetry))
            loop.close()
        except Exception as e:
            logger.error(f"❌ Error en message handler: {e}")

    return sync_handler
