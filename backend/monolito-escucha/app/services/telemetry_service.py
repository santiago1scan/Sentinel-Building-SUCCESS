"""Telemetry service - store bridge messages in the 26-Oct structure and run the alert engine.

Two kinds of message (message_type):
- out_of_range: an incident sent as soon as the bridge detects it; each value is raw and carries its exact time
  (generated_at of the message).
- half_hour_summary: avg/max/min of each variable (`<variable>__avg|max|min`) plus booleans such as battery_low;
  the readings are dated at the start of the window.
Any other message type is stored the same way, keys as they come (no alert unless a key matches a known range).
"""
import decimal
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.alert_engine import BATTERY_LOW, ON_BATTERY_POWER, AlertEngine
from app.analytics.connectivity import open_session as open_connectivity_session
from app.analytics.metrics import parse_sensor_values
from app.models.ingest_message import IngestMessage
from app.models.reading import Reading
from app.repositories.analytics_repositories import (AlertRepository, IngestMessageRepository,
                                                     SensorMetricRepository)
from app.repositories.building_repository import BuildingRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.reading import ReadingRead
from app.services.DTOS.telemetry_dto import BridgeDTO, SensorDTO, TelemetryAggregateDTO

logger = logging.getLogger(__name__)

# Yes/no flags of the node's power -> the technical notice each one opens.
BOOLEAN_METRICS = {"battery_low": BATTERY_LOW, "power_source": ON_BATTERY_POWER}


class TelemetryService:
    def __init__(
        self,
        building_repo: BuildingRepository,
        zone_repo: ZoneRepository,
        node_repo: NodeRepository,
        sensor_repo: SensorRepository,
        sensor_type_repo: SensorTypeRepository,
        reading_repo: ReadingRepository,
        clock: Callable[[], datetime] | None = None,
    ):
        self.building_repo = building_repo
        self.zone_repo = zone_repo
        self.node_repo = node_repo
        self.sensor_repo = sensor_repo
        self.sensor_type_repo = sensor_type_repo
        self.reading_repo = reading_repo
        self.session: AsyncSession = reading_repo.session
        self.message_repo = IngestMessageRepository(self.session)
        self.metric_repo = SensorMetricRepository(self.session)
        self.engine = AlertEngine(AlertRepository(self.session))
        # Server time of arrival. Silence is measured with it, never with the bridge clock (a Raspberry Pi has
        # no battery clock and can drift; review D4, 13-Nov-2026).
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def for_session(cls, session: AsyncSession,
                    clock: Callable[[], datetime] | None = None) -> "TelemetryService":
        return cls(BuildingRepository(session), ZoneRepository(session), NodeRepository(session),
                   SensorRepository(session), SensorTypeRepository(session), ReadingRepository(session),
                   clock=clock)

    async def process_telemetry(self, telemetry: TelemetryAggregateDTO) -> dict:
        """Store the message and its readings, then group/alert. Does not commit (the caller does)."""
        results = {"message_uid": telemetry.message_uid, "duplicate": False, "readings_created": 0,
                   "alerts_opened": 0, "errors": []}

        if await self.message_repo.get_by_uid(telemetry.message_uid):
            results["duplicate"] = True
            return results

        # Unknown node: store nothing, so the bridge's retry after the node is registered is not a "duplicate"
        # and its data is not lost (review D5).
        nodes = {}
        for bridge in telemetry.bridges:
            nodes[bridge.node_code] = await self.node_repo.get_by_code(bridge.node_code)
        missing = [code for code, node in nodes.items() if node is None]
        if missing:
            results["errors"].append(f"Receiving node not found: {', '.join(missing)} (message not stored)")
            return results
        heard_at = self.clock()

        message = await self.message_repo.add(IngestMessage(
            message_uid=telemetry.message_uid, building_code=telemetry.building_code,
            message_type=str(getattr(telemetry.message_type, "value", telemetry.message_type)),
            schema_version=telemetry.schema_version, sequence_number=telemetry.sequence_number,
            priority=str(getattr(telemetry.priority, "value", telemetry.priority)),
            quality=str(getattr(telemetry.quality, "value", telemetry.quality)),
            transport=telemetry.transport, generated_at=telemetry.generated_at, sent_at=telemetry.sent_at,
            window_start=telemetry.window.start, window_end=telemetry.window.end,
            sample_count_bridge=telemetry.window.sample_count,
        ))

        for bridge in telemetry.bridges:
            try:
                await self._process_bridge(bridge, nodes[bridge.node_code], heard_at, telemetry, message, results)
            except Exception as e:  # one bad bridge must not lose the rest of the message
                results["errors"].append(f"Error processing bridge {bridge.node_code}: {e}")
        return results

    async def _process_bridge(self, bridge: BridgeDTO, node, heard_at: datetime,
                              telemetry: TelemetryAggregateDTO, message: IngestMessage, results: dict) -> None:
        if node.last_signal_received_at is None or heard_at > node.last_signal_received_at:
            node.last_signal_received_at = heard_at
        await self.engine.on_node_heard(node.node_id, heard_at)
        await open_connectivity_session(self.session, node.node_id, heard_at)

        for sensor_dto in bridge.sensors:
            try:
                async with self.session.begin_nested():
                    await self._process_sensor(sensor_dto, node.node_id, telemetry, message, results)
            except Exception as e:
                results["errors"].append(f"Error processing sensor {sensor_dto.sensor_code}: {e}")
        # After all the node's sensors: a fire shows up as heat AND air quality, maybe from two sensors.
        await self.engine.apply_severity(node.node_id)
        await self.session.flush()

    async def _process_sensor(self, sensor_dto: SensorDTO, node_id: int, telemetry: TelemetryAggregateDTO,
                              message: IngestMessage, results: dict) -> None:
        sensor = await self.sensor_repo.get_by_code(sensor_dto.sensor_code)
        if not sensor:
            raise RuntimeError(f"Sensor not found: {sensor_dto.sensor_code}")

        summary: dict[int, dict] = defaultdict(dict)
        for value in parse_sensor_values(sensor_dto.data):
            metric = await self.metric_repo.get_or_create(sensor.sensor_type_id, value.metric_code)
            at = telemetry.generated_at if value.aggregation == "raw" else telemetry.window.start
            reading = Reading(
                message_id=message.message_id, sensor_id=sensor.sensor_id, receiving_node_id=node_id,
                metric_id=metric.metric_id, aggregation=value.aggregation, measured_at=at,
                measured_value=decimal.Decimal(str(value.value)), sample_count_sensor=sensor_dto.sample_count,
            )
            self.session.add(reading)
            await self.session.flush()
            results["readings_created"] += 1

            if value.aggregation != "raw":
                summary[metric.metric_id]["metric"] = metric
                summary[metric.metric_id][value.aggregation] = value.value
            elif value.metric_code in BOOLEAN_METRICS:
                await self.engine.on_battery(node_id, sensor.sensor_id, metric, value.value, telemetry.generated_at,
                                             code=BOOLEAN_METRICS[value.metric_code])
            else:
                alert = await self.engine.on_raw(sensor.sensor_id, node_id, metric, value.value,
                                                 telemetry.generated_at, reading_id=reading.reading_id)
                if alert is not None:
                    if alert.reading_count == 1:
                        results["alerts_opened"] += 1
                    reading.alert_id = alert.alert_id

        for parts in summary.values():
            await self.engine.on_summary(sensor.sensor_id, node_id, parts["metric"], avg=parts.get("avg"),
                                         max_=parts.get("max"), min_=parts.get("min"),
                                         window_end=telemetry.window.end)
        await self.session.flush()

    async def get_telemetry_by_node(
        self, node_id: int, limit: int = 100, offset: int = 0
    ) -> dict:
        """Get complete telemetry information for a node with all related data."""
        node = await self.node_repo.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        zone = await self.zone_repo.get(node.zone_id)
        floor = await self.zone_repo.get_floor(zone) if zone else None
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
                "floor": floor.level if floor else None,
                "floor_name": floor.name if floor else None,
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

