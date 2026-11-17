"""Sensor types with the variables they measure (GET /sensor-types), against a real PostgreSQL.

Case of 16-Nov-2026: the node registration screen had no way to read the seeded metrics and their ranges.
"""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import require_user
from app.core.database import get_db
from app.core.firebase_auth import FirebaseUser
from app.main import app
from app.models import Building, Node, Sensor, SensorType, Zone
from tests.db.conftest import TEST_DATABASE_URL, areset_schema


@pytest_asyncio.fixture
async def api():
    await areset_schema()
    engine = create_async_engine(TEST_DATABASE_URL)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        async def override():
            yield s
            await s.commit()

        app.dependency_overrides[get_db] = override
        app.dependency_overrides[require_user] = lambda: FirebaseUser(uid="admin", email="a@example.com",
                                                                      email_verified=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, s
        app.dependency_overrides.clear()
    await engine.dispose()


async def test_list_brings_each_type_with_its_metrics_and_ranges(api):
    client, _ = api
    response = await client.get("/sensor-types")

    assert response.status_code == 200, response.text
    types = {t["name"]: t for t in response.json()}
    assert set(types) == {"ADXL355", "AMG8833", "BME688", "INA219"}
    assert sum(len(t["metrics"]) for t in types.values()) == 18

    bme = {m["metric_code"]: m for m in types["BME688"]["metrics"]}
    assert list(bme) == ["temperature_c", "humidity_percent", "pressure_hpa", "iaq_index", "tvoc_ppb"]
    assert (float(bme["temperature_c"]["normal_minimum"]), float(bme["temperature_c"]["normal_maximum"])) == (10, 31)
    assert bme["temperature_c"]["unit"] == "°C"
    assert bme["iaq_index"]["alarm_below"] is False
    assert bme["pressure_hpa"]["normal_minimum"] is None and bme["pressure_hpa"]["normal_maximum"] is None
    assert bme["tvoc_ppb"]["normal_minimum"] is None


async def test_one_type_brings_its_metrics_and_unknown_is_404(api):
    client, s = api
    adxl = (await s.execute(select(SensorType).where(SensorType.name == "ADXL355"))).scalar_one()

    response = await client.get(f"/sensor-types/{adxl.sensor_type_id}")
    assert response.status_code == 200
    assert [m["metric_code"] for m in response.json()["metrics"]] == ["x_g", "y_g", "z_g", "rms_g", "frequency_hz"]

    assert (await client.get("/sensor-types/999999")).status_code == 404


async def test_create_still_answers_without_metrics(api):
    client, _ = api
    response = await client.post("/sensor-types", json={"name": "SCD41", "sampling_interval": 30})
    assert response.status_code == 201, response.text
    assert "metrics" not in response.json()


async def test_sensors_of_a_type_are_sensors_not_the_type(api):
    """It returned the sensor type itself, declared as a list of types."""
    client, s = api
    adxl = (await s.execute(select(SensorType).where(SensorType.name == "ADXL355"))).scalar_one()
    building = Building(name="Sentinel")
    s.add(building)
    await s.flush()
    zone = Zone(building_id=building.building_id, name="Z-1")
    s.add(zone)
    await s.flush()
    node = Node(code="NODE-1", name="Nodo 1", zone_id=zone.zone_id)
    s.add(node)
    await s.flush()
    s.add(Sensor(code="ACC-1", primary_node_id=node.node_id, sensor_type_id=adxl.sensor_type_id))
    await s.commit()

    response = await client.get(f"/sensor-types/{adxl.sensor_type_id}/sensors")
    assert response.status_code == 200, response.text
    assert [x["code"] for x in response.json()] == ["ACC-1"]


async def test_patch_still_answers_without_metrics(api):
    client, s = api
    bme = (await s.execute(select(SensorType).where(SensorType.name == "BME688"))).scalar_one()
    response = await client.patch(f"/sensor-types/{bme.sensor_type_id}", json={"sampling_interval": 60})
    assert response.status_code == 200, response.text
    assert response.json()["sampling_interval"] == 60
    assert "metrics" not in response.json()
