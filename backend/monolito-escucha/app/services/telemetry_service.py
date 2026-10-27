"""Telemetry service - Process and save telemetry data from bridge."""
import decimal
from datetime import datetime
from collections.abc import Sequence

from app.repositories.building_repository import BuildingRepository
from app.repositories.zone_repository import ZoneRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.reading_repository import ReadingRepository
from app.services.DTOS.telemetry_dto import TelemetryAggregateDTO, SensorDTO, BridgeDTO
from app.schemas.reading import ReadingCreate, ReadingRead


class TelemetryService:
    def __init__(
        self,
        building_repo: BuildingRepository,
        zone_repo: ZoneRepository,
        node_repo: NodeRepository,
        sensor_repo: SensorRepository,
        sensor_type_repo: SensorTypeRepository,
        reading_repo: ReadingRepository,
    ):
        self.building_repo = building_repo
        self.zone_repo = zone_repo
        self.node_repo = node_repo
        self.sensor_repo = sensor_repo
        self.sensor_type_repo = sensor_type_repo
        self.reading_repo = reading_repo

    async def process_telemetry(self, telemetry: TelemetryAggregateDTO) -> dict:
        """Process incoming telemetry data and save to database."""
        try:
            results = {
                "message_uid": telemetry.message_uid,
                "readings_created": 0,
                "errors": [],
            }

            for bridge in telemetry.bridges:
                try:
                    readings_from_bridge = await self._process_bridge(bridge)
                    results["readings_created"] += readings_from_bridge
                except Exception as e:
                    results["errors"].append(
                        f"Error processing bridge {bridge.node_code}: {str(e)}"
                    )

            return results

        except Exception as e:
            raise RuntimeError(f"Error processing telemetry: {str(e)}")

    async def _process_bridge(self, bridge: BridgeDTO) -> int:
        """Process a single bridge and its sensors."""
        readings_count = 0

        for sensor_dto in bridge.sensors:
            try:
                readings_from_sensor = await self._process_sensor(
                    sensor_dto, bridge.node_code
                )
                readings_count += readings_from_sensor
            except Exception as e:
                raise RuntimeError(
                    f"Error processing sensor {sensor_dto.sensor_code}: {str(e)}"
                )

        return readings_count

    async def _process_sensor(self, sensor_dto: SensorDTO, receiving_node_code: str) -> int:
        """Process a single sensor's data and create readings."""
        import logging
        logger = logging.getLogger(__name__)
        readings_count = 0

        sensor_code = sensor_dto.sensor_code
        sensor = await self.sensor_repo.get_by_code(sensor_code)

        if not sensor:
            raise RuntimeError(f"Sensor not found: {sensor_code}")

        receiving_node = await self.node_repo.get_by_code(receiving_node_code)
        if not receiving_node:
            raise RuntimeError(f"Receiving node not found: {receiving_node_code}")

        measured_value = self._extract_primary_value(sensor_dto)
        logger.info(f"🔍 Extracted value for {sensor_code}: {measured_value}")

        if measured_value is None:
            logger.warning(f"⚠️  No primary value found in sensor data: {sensor_dto.data}")
            return 0

        reading_in = ReadingCreate(
            sensor_id=sensor.sensor_id,
            receiving_node_id=receiving_node.node_id,
            measured_at=datetime.utcnow(),
            measured_value=decimal.Decimal(str(measured_value)),
            sequence_number=sensor_dto.sample_count,
        )

        created_reading = await self.reading_repo.create(reading_in)
        logger.info(f"✅ Created reading: {created_reading}")

        if created_reading:
            readings_count += 1

        return readings_count

    async def get_telemetry_by_node(
        self, node_id: int, limit: int = 100, offset: int = 0
    ) -> dict:
        """Get complete telemetry information for a node with all related data."""
        node = await self.node_repo.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        zone = await self.zone_repo.get(node.zone_id)
        building = await self.building_repo.get(zone.building_id) if zone else None

        readings = await self.reading_repo.get_by_receiving_node(node_id, limit, offset)

        readings_with_details = []
        for reading in readings:
            sensor = await self.sensor_repo.get(reading.sensor_id)
            sensor_type = (
                await self.sensor_type_repo.get(sensor.sensor_type_id) if sensor else None
            )
            primary_node = await self.node_repo.get(sensor.primary_node_id) if sensor else None

            reading_detail = {
                "reading": ReadingRead.model_validate(reading),
                "sensor": {
                    "sensor_id": sensor.sensor_id,
                    "code": sensor.code,
                    "connection_type": sensor.connection_type,
                    "connection_address": sensor.connection_address,
                    "sensor_type": {
                        "sensor_type_id": sensor_type.sensor_type_id,
                        "name": sensor_type.name,
                        "sampling_interval": sensor_type.sampling_interval,
                        "default_unit": sensor_type.default_unit,
                        "normal_minimum": float(sensor_type.normal_minimum)
                        if sensor_type.normal_minimum
                        else None,
                        "normal_maximum": float(sensor_type.normal_maximum)
                        if sensor_type.normal_maximum
                        else None,
                    }
                    if sensor_type
                    else None,
                    "primary_node": {
                        "node_id": primary_node.node_id,
                        "code": primary_node.code,
                        "name": primary_node.name,
                    }
                    if primary_node
                    else None,
                },
            }
            readings_with_details.append(reading_detail)

        return {
            "node": {
                "node_id": node.node_id,
                "code": node.code,
                "name": node.name,
                "ip_address": str(node.ip_address) if node.ip_address else None,
                "local_storage_mb": float(node.local_storage_mb)
                if node.local_storage_mb
                else None,
                "registered_at": node.registered_at,
                "last_signal_received_at": node.last_signal_received_at,
            },
            "zone": {
                "zone_id": zone.zone_id,
                "code": zone.name,
                "floor": zone.floor,
            }
            if zone
            else None,
            "building": {
                "building_id": building.building_id,
                "name": building.name,
                "address": building.address,
            }
            if building
            else None,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(readings_with_details),
            },
            "telemetry_readings": readings_with_details,
        }

    @staticmethod
    def _extract_primary_value(sensor_dto: SensorDTO) -> float | None:
        """Extract the primary measured value from sensor data based on type."""
        data = sensor_dto.data

        # Priority field names to search
        priority_keys = [
            "temperature_avg_c", "average_avg_c",  # Temperature
            "iaq_avg",  # Air quality
            "rms_avg_g", "x_avg_g", "y_avg_g", "z_avg_g",  # Motion/Acceleration
            "voltage_avg_v", "current_avg_ma", "power_avg_mw",  # Electrical
            "value"  # Generic
        ]

        if isinstance(data, dict):
            for key in priority_keys:
                if key in data and data[key] is not None:
                    return data[key]
            # If no specific field found, return first numeric value
            for v in data.values():
                if isinstance(v, (int, float)):
                    return v
            return None

        # Handle Pydantic model objects (typed sensor data)
        for key in priority_keys:
            value = getattr(data, key, None)
            if value is not None:
                return value

        # Fallback: try to get any numeric attribute
        for attr_name in dir(data):
            if not attr_name.startswith('_'):
                value = getattr(data, attr_name, None)
                if isinstance(value, (int, float)) and value is not None:
                    return value

        return None

        value = getattr(data, "iaq_avg", None)  # Air quality
        if value is not None:
            return value

        value = getattr(data, "rms_avg_g", None)  # Motion
        if value is not None:
            return value

        value = getattr(data, "voltage_avg_v", None)  # Electrical
        if value is not None:
            return value

        return None
