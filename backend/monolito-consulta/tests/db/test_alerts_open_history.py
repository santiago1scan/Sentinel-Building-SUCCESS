"""Open alerts for the guard, marking them as handled, and the half-hour history, against a real PostgreSQL."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import require_user
from app.core.database import get_db
from app.core.firebase_auth import FirebaseUser
from app.main import app
from app.models import (Alert, AppRole, AppUser, Building, Floor, IngestMessage, Node, Reading, Sensor,
                        SensorMetric, SensorType, Zone)
from tests.db.conftest import TEST_DATABASE_URL, areset_schema

T0 = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def seeded():
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
        node = Node(code="NODE-FLOOR-1", name="Bridge piso 1", zone_id=zone.zone_id)
        stype = SensorType(name="BME688", sampling_interval=1)
        role = AppRole(role_code=1, name="Guarda")  # BIGINT in the backend, VARCHAR in success_db.sql
        s.add_all([node, stype, role])
        await s.flush()
        sensor = Sensor(code="GAS-F1", primary_node_id=node.node_id, sensor_type_id=stype.sensor_type_id)
        temp = SensorMetric(sensor_type_id=stype.sensor_type_id, metric_code="temperature_c", unit="°C",
                            normal_minimum=Decimal(10), normal_maximum=Decimal(31))
        iaq = SensorMetric(sensor_type_id=stype.sensor_type_id, metric_code="iaq_index", unit="IAQ",
                           normal_minimum=Decimal(51), normal_maximum=Decimal(100), alarm_below=False)
        guard = AppUser(email="guarda@example.com", full_name="Guarda", password_hash="x", role_code=1)
        s.add_all([sensor, temp, iaq, guard])
        await s.flush()

        # Half-hour summaries for 10:00-13:00, the 11:00-11:30 one missing.
        for i in range(6):
            start = T0 + timedelta(minutes=30 * i)
            if i == 2:
                continue
            msg = IngestMessage(message_uid=f"s-{i}", message_type="half_hour_summary", schema_version="1.0",
                                generated_at=start + timedelta(minutes=30), window_start=start,
                                window_end=start + timedelta(minutes=30))
            s.add(msg)
            await s.flush()
            for agg, value in (("avg", 21 + i), ("max", 24 + i), ("min", 18 + i)):
                s.add(Reading(message_id=msg.message_id, sensor_id=sensor.sensor_id,
                              receiving_node_id=node.node_id, metric_id=temp.metric_id, aggregation=agg,
                              measured_at=start, measured_value=Decimal(value)))

        def alert(code, metric, peak, dev, start, alert_type="out_of_range", direction="above"):
            return Alert(event_uuid=code + str(start), alert_code=code, alert_type=alert_type, direction=direction,
                         node_id=node.node_id, sensor_id=sensor.sensor_id, metric_id=metric.metric_id,
                         started_at=start, last_seen_at=start, generated_at=start, peak_value=Decimal(peak),
                         deviation=Decimal(dev), reading_count=1)

        small = alert("OUT_OF_RANGE_ABOVE", temp, 33, "0.0952", T0 + timedelta(minutes=40))
        big = alert("OUT_OF_RANGE_ABOVE", iaq, 300, "4.0816", T0 + timedelta(minutes=45))
        tech = alert("SENSOR_STUCK", temp, 22, "0", T0 + timedelta(minutes=50), alert_type="technical",
                     direction=None)
        closed = alert("OUT_OF_RANGE_ABOVE", temp, 40, "9", T0)
        closed.ended_at = T0 + timedelta(minutes=10)
        # Another building with its own open alert: it must not count as "other open" for the first building.
        other_building = Building(name="Otro edificio")
        s.add(other_building)
        await s.flush()
        other_floor = Floor(building_id=other_building.building_id, level=1, name="Primer piso")
        s.add(other_floor)
        await s.flush()
        other_zone = Zone(building_id=other_building.building_id, name="Piso 1", floor_id=other_floor.floor_id)
        s.add(other_zone)
        await s.flush()
        other_node = Node(code="NODE-OTHER", name="Bridge otro", zone_id=other_zone.zone_id)
        s.add(other_node)
        await s.flush()
        elsewhere = Alert(event_uuid="elsewhere", alert_code="NODE_SILENT", alert_type="technical",
                          node_id=other_node.node_id, started_at=T0 + timedelta(minutes=55),
                          last_seen_at=T0 + timedelta(minutes=55), generated_at=T0 + timedelta(minutes=55))
        s.add_all([small, big, tech, closed, elsewhere])
        await s.commit()
        ids = {"small": small.alert_id, "big": big.alert_id, "tech": tech.alert_id, "closed": closed.alert_id,
               "elsewhere": elsewhere.alert_id, "guard": guard.user_id, "sensor": sensor.sensor_id}

        async def override():
            yield s
            await s.commit()

        app.dependency_overrides[get_db] = override
        # The routes require a Firebase login since 89f7e43; here a signed-in guard is assumed.
        app.dependency_overrides[require_user] = lambda: FirebaseUser(uid="guard", email="guarda@example.com",
                                                                      email_verified=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, ids
        app.dependency_overrides.clear()
    await engine.dispose()


async def test_open_alerts_put_emergencies_first_and_the_biggest_deviation_on_top(seeded):
    client, ids = seeded
    response = await client.get("/alerts/open")
    assert response.status_code == 200, response.text
    body = response.json()

    # The short event that already ended is still shown until the guard handles it (review D1).
    assert [a["alert_id"] for a in body] == [ids["closed"], ids["big"], ids["small"], ids["elsewhere"], ids["tech"]]
    top = body[1]
    assert top["metric_code"] == "iaq_index" and top["unit"] == "IAQ"
    assert (top["normal_minimum"], top["normal_maximum"]) == (51, 100)
    assert top["floor"] == 1 and top["floor_name"] == "Primer piso" and top["zone_name"] == "Piso 1"
    assert top["node_code"] == "NODE-FLOOR-1" and top["sensor_code"] == "GAS-F1"
    assert top["peak_value"] == 300
    assert top["other_open_count"] == 3  # same building only (review D2)
    assert body[3]["other_open_count"] == 0  # the alert of the other building


async def test_ended_and_handled_alert_leaves_the_open_list(seeded):
    client, ids = seeded
    await client.post(f"/alerts/{ids['closed']}/handle")
    open_ids = [a["alert_id"] for a in (await client.get("/alerts/open")).json()]
    assert ids["closed"] not in open_ids


async def test_handle_records_who_and_when_and_keeps_the_event_open(seeded):
    client, ids = seeded
    # The guard comes from the Firebase token, not from the body: a user_id in the body is ignored (security review).
    response = await client.post(f"/alerts/{ids['big']}/handle", json={"user_id": 999999})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handled_by_user_id"] == ids["guard"]
    assert body["handled_at"] is not None
    assert body["ended_at"] is None  # handling does not close the event

    open_ids = [a["alert_id"] for a in (await client.get("/alerts/open")).json()]
    assert ids["big"] in open_ids  # still shown while the data is out of range


async def test_handle_unknown_alert_is_404(seeded):
    client, ids = seeded
    response = await client.post("/alerts/999999/handle")
    assert response.status_code == 404


async def test_handle_by_a_login_without_app_user_is_403(seeded):
    client, ids = seeded
    app.dependency_overrides[require_user] = lambda: FirebaseUser(uid="x", email="nadie@example.com",
                                                                  email_verified=True)
    response = await client.post(f"/alerts/{ids['big']}/handle")
    assert response.status_code == 403


async def test_handle_with_unverified_email_is_403(seeded):
    client, ids = seeded
    app.dependency_overrides[require_user] = lambda: FirebaseUser(uid="x", email="guarda@example.com",
                                                                  email_verified=False)
    response = await client.post(f"/alerts/{ids['big']}/handle")
    assert response.status_code == 403


async def test_history_lists_every_half_hour_and_marks_the_missing_one(seeded):
    client, ids = seeded
    response = await client.get("/history", params={
        "sensor_id": ids["sensor"], "metric_code": "temperature_c",
        "from": T0.isoformat(), "to": (T0 + timedelta(hours=3)).isoformat()})
    assert response.status_code == 200, response.text
    rows = response.json()

    assert len(rows) == 6
    assert [r["no_data"] for r in rows] == [False, False, True, False, False, False]
    assert (rows[0]["avg"], rows[0]["max"], rows[0]["min"]) == (21, 24, 18)
    assert rows[2]["avg"] is None
    assert rows[1]["alert_ids"] == sorted([ids["small"], ids["tech"]])  # alerts that touched 10:30-11:00
    assert ids["closed"] in rows[0]["alert_ids"]


async def test_history_unknown_metric_is_404(seeded):
    client, ids = seeded
    response = await client.get("/history", params={
        "sensor_id": ids["sensor"], "metric_code": "nope", "from": T0.isoformat(),
        "to": (T0 + timedelta(hours=1)).isoformat()})
    assert response.status_code == 404


async def test_unhandled_route_is_reachable(seeded):
    """Real case (13-Nov-2026): /alerts/unhandled was declared after /{alert_id} and always answered 422."""
    client, ids = seeded
    response = await client.get("/alerts/unhandled")
    assert response.status_code == 200, response.text
    assert {a["alert_id"] for a in response.json()} == {ids["small"], ids["big"], ids["tech"], ids["closed"],
                                                        ids["elsewhere"]}
