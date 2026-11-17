"""Ingest of incidents and half-hour summaries into the 26-Oct structure, against a real PostgreSQL."""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (Alert, Building, Floor, IngestMessage, Node, Reading, Sensor, SensorMetric, SensorType,
                        Zone)
from app.services.DTOS.telemetry_dto import TelemetryAggregateDTO
from app.services.telemetry_service import TelemetryService
from tests.db.conftest import TEST_DATABASE_URL, areset_schema

pytestmark = pytest.mark.asyncio
T0 = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
NODE_CODE, GAS, POWER = "NODE-FLOOR-1", "GAS-F1", "PWR-F1"


@pytest_asyncio.fixture
async def session():
    await areset_schema()
    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        building = Building(name="Sentinel")
        s.add(building)
        await s.flush()
        floor = Floor(building_id=building.building_id, level=1, name="Primer piso")
        s.add(floor)
        await s.flush()
        zone = Zone(building_id=building.building_id, name="Piso 1", floor_id=floor.floor_id)
        s.add(zone)
        await s.flush()
        node = Node(code=NODE_CODE, name="Bridge piso 1", zone_id=zone.zone_id)
        # The types come from the seeded sensor catalog (migration c3f8a2d6b9e1), with their metrics and ranges.
        gas_type = (await s.execute(select(SensorType).where(SensorType.name == "BME688"))).scalar_one()
        power_type = (await s.execute(select(SensorType).where(SensorType.name == "INA219"))).scalar_one()
        s.add(node)
        await s.flush()
        s.add_all([
            Sensor(code=GAS, primary_node_id=node.node_id, sensor_type_id=gas_type.sensor_type_id),
            Sensor(code=POWER, primary_node_id=node.node_id, sensor_type_id=power_type.sensor_type_id),
        ])
        await s.commit()
        yield s
    await engine.dispose()


def message(uid: str, message_type: str, at: datetime, sensors: list[tuple[str, str, dict]],
            window_minutes: int = 0, node_code: str = NODE_CODE) -> TelemetryAggregateDTO:
    start = at - timedelta(minutes=window_minutes)
    return TelemetryAggregateDTO.model_validate({
        "schema_version": "1.0", "message_uid": uid, "message_type": message_type,
        "building_uid": "bld-1", "building_code": "SB-001", "generated_at": at.isoformat(),
        "sent_at": at.isoformat(), "sequence_number": 1, "priority": "normal", "quality": "valid",
        "delivery_policy": "best_effort", "delivery_status": "sent", "transport": "rest",
        "window": {"start": start.isoformat(), "end": at.isoformat(),
                   "duration_seconds": window_minutes * 60.0, "sample_count": 1},
        "bridges": [{
            "node_uid": "uid-1", "node_code": node_code, "node_name": "Bridge", "floor": 1,
            "zone_uid": "z-1", "zone_code": "Z-1",
            "sensors": [{"sensor_uid": f"uid-{code}", "sensor_code": code, "sensor_model": model,
                         "measurement_type": "air_quality", "sample_count": 1, "data": data}
                        for code, model, data in sensors],
        }],
    })


def summary(uid: str, at: datetime, temp=(21.5, 24.0, 19.0), battery=False) -> TelemetryAggregateDTO:
    avg, mx, mn = temp
    return message(uid, "half_hour_summary", at, [
        (GAS, "BME688", {"temperature_c__avg": avg, "temperature_c__max": mx, "temperature_c__min": mn,
                         "humidity_percent__avg": 85, "humidity_percent__max": 90, "humidity_percent__min": 80,
                         "iaq_index__avg": 70, "iaq_index__max": 90, "iaq_index__min": 55}),
        (POWER, "INA219", {"bus_voltage_v__avg": 12.1, "bus_voltage_v__max": 12.3, "bus_voltage_v__min": 11.9,
                           "battery_low": battery}),
    ], window_minutes=30)


def incident(uid: str, at: datetime, data: dict) -> TelemetryAggregateDTO:
    return message(uid, "out_of_range", at, [(GAS, "BME688", data)])


async def count(session, model, *where) -> int:
    return (await session.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def ingest(session, dto, now=None):
    """`now` is the server clock at arrival (defaults to the message time)."""
    clock = (lambda: now) if now is not None else (lambda: dto.generated_at)
    result = await TelemetryService.for_session(session, clock=clock).process_telemetry(dto)
    await session.commit()
    return result


async def test_summary_stores_one_row_per_variable_and_aggregation_plus_battery(session):
    result = await ingest(session, summary("s-1", T0))

    assert result["errors"] == [] and result["duplicate"] is False
    # 3 gas variables x 3 aggregations + voltage x 3 + battery_low = 13
    assert result["readings_created"] == 13
    assert await count(session, Reading) == 13
    rows = (await session.execute(
        select(SensorMetric.metric_code, Reading.aggregation, Reading.measured_value, Reading.measured_at)
        .join(SensorMetric, SensorMetric.metric_id == Reading.metric_id)
        .where(SensorMetric.metric_code == "temperature_c"))).all()
    assert {(r.aggregation, float(r.measured_value)) for r in rows} == {("avg", 21.5), ("max", 24.0), ("min", 19.0)}
    assert all(r.measured_at == T0 - timedelta(minutes=30) for r in rows)  # window start
    battery = (await session.execute(select(Reading.measured_value).join(SensorMetric).where(
        SensorMetric.metric_code == "battery_low"))).scalar_one()
    assert float(battery) == 0
    message_row = (await session.execute(select(IngestMessage))).scalar_one()
    assert message_row.message_type == "half_hour_summary"
    assert (message_row.window_start, message_row.window_end) == (T0 - timedelta(minutes=30), T0)


async def test_same_message_twice_does_not_duplicate(session):
    dto = incident("i-1", T0, {"temperature_c": 40})
    await ingest(session, dto)
    again = await ingest(session, dto)

    assert again["duplicate"] is True and again["readings_created"] == 0
    assert await count(session, Reading) == 1
    assert await count(session, Alert) == 1
    assert await count(session, IngestMessage) == 1


async def test_incidents_are_grouped_and_linked_to_their_alert(session):
    for i, value in enumerate([35, 40, 38]):
        await ingest(session, incident(f"i-{i}", T0 + timedelta(minutes=i), {"temperature_c": value}))

    alert = (await session.execute(select(Alert))).scalar_one()
    assert (alert.reading_count, float(alert.peak_value), alert.ended_at) == (3, 40, None)
    assert alert.started_at == T0 and alert.last_seen_at == T0 + timedelta(minutes=2)
    assert await count(session, Reading, Reading.alert_id == alert.alert_id) == 3
    raw_times = (await session.execute(select(Reading.measured_at).order_by(Reading.measured_at))).scalars().all()
    assert raw_times == [T0, T0 + timedelta(minutes=1), T0 + timedelta(minutes=2)]  # incident time, not arrival

    await ingest(session, summary("s-1", T0 + timedelta(minutes=30), temp=(25, 30, 20)))
    await session.refresh(alert)
    assert alert.ended_at == T0 + timedelta(minutes=30)


async def test_battery_low_in_summary_opens_a_technical_alert(session):
    await ingest(session, summary("s-1", T0, battery=True))
    alert = (await session.execute(select(Alert))).scalar_one()
    assert (alert.alert_type, alert.alert_code) == ("technical", "BATTERY_LOW")


async def test_unknown_variable_is_created_without_range_and_opens_nothing(session):
    result = await ingest(session, incident("i-1", T0, {"co2_ppm": 5000}))

    assert result["errors"] == []
    metric = (await session.execute(select(SensorMetric).where(SensorMetric.metric_code == "co2_ppm"))).scalar_one()
    assert metric.normal_minimum is None and metric.normal_maximum is None
    assert await count(session, Alert) == 0


async def test_known_variable_gets_the_excel_range(session):
    await ingest(session, incident("i-1", T0, {"iaq_index": 30}))
    metric = (await session.execute(select(SensorMetric).where(SensorMetric.metric_code == "iaq_index"))).scalar_one()
    assert (float(metric.normal_minimum), float(metric.normal_maximum), metric.alarm_below) == (51, 100, False)
    assert await count(session, Alert) == 0


async def test_unknown_sensor_is_reported_and_the_rest_is_saved(session):
    dto = message("i-1", "out_of_range", T0, [("NOPE", "X", {"temperature_c": 40}),
                                              (GAS, "BME688", {"temperature_c": 41})])
    result = await ingest(session, dto)

    assert any("NOPE" in e for e in result["errors"])
    assert await count(session, Reading) == 1
    assert await count(session, Alert) == 1


async def test_node_last_signal_is_the_server_arrival_time_not_the_bridge_clock(session):
    """Review D4: a Raspberry Pi has no battery clock; a bridge 40 min late must not look silent."""
    await ingest(session, summary("s-1", T0 - timedelta(minutes=40)), now=T0)
    node = (await session.execute(select(Node))).scalar_one()
    assert node.last_signal_received_at == T0


async def test_message_from_an_unregistered_node_is_not_marked_as_seen(session):
    """Review D5: otherwise the bridge's retry after registering the node answers duplicate and the data is lost."""
    dto = message("i-1", "out_of_range", T0, [(GAS, "BME688", {"temperature_c": 40})], node_code="NODE-NEW")
    result = await ingest(session, dto)

    assert result["readings_created"] == 0 and any("NODE-NEW" in e for e in result["errors"])
    assert await count(session, IngestMessage) == 0

    node = (await session.execute(select(Node))).scalar_one()
    node.code = "NODE-NEW"  # the node gets registered
    await session.commit()
    retry = await ingest(session, dto)
    assert retry["duplicate"] is False and retry["readings_created"] == 1


async def test_mqtt_path_commits_what_it_stores(session):
    """Real case (13-Nov-2026): the MQTT handler processed messages but never committed, so nothing stayed."""
    from app.core.mqtt_handler import MQTTMessageHandler

    handler = object.__new__(MQTTMessageHandler)  # no worker thread: call the processing step directly
    engine = create_async_engine(TEST_DATABASE_URL)
    handler.AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await handler._process_message(incident("mqtt-1", T0, {"temperature_c": 40}))
    await engine.dispose()

    assert await count(session, Reading) == 1


async def test_power_source_battery_is_stored_as_1_and_opens_a_notice(session):
    """Business rule (14-Nov-2026): power_source is kept like battery_low (it used to be dropped)."""
    await ingest(session, message("p-1", "out_of_range", T0, [(POWER, "INA219", {"power_source": "battery"})]))
    stored = (await session.execute(select(Reading.measured_value).join(SensorMetric).where(
        SensorMetric.metric_code == "power_source"))).scalar_one()
    assert float(stored) == 1
    alert = (await session.execute(select(Alert))).scalar_one()
    assert (alert.alert_type, alert.alert_code, alert.ended_at) == ("technical", "ON_BATTERY_POWER", None)

    await ingest(session, message("p-2", "out_of_range", T0 + timedelta(minutes=3),
                                  [(POWER, "INA219", {"power_source": "main"})]))
    await session.refresh(alert)
    assert alert.ended_at == T0 + timedelta(minutes=3)


async def test_telemetry_by_node_reports_the_floor_of_its_zone(session):
    node = (await session.execute(select(Node).where(Node.code == NODE_CODE))).scalar_one()

    data = await TelemetryService.for_session(session).get_telemetry_by_node(node.node_id)

    assert data["zone"]["floor"] == 1
    assert data["zone"]["floor_name"] == "Primer piso"
