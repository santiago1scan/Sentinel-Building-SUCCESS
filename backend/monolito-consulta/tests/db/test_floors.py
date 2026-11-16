"""Floors against a real PostgreSQL: the API, what the database itself enforces, and the data migration."""
import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import require_user
from app.core.database import get_db
from app.core.firebase_auth import FirebaseUser
from app.main import app
from app.models import Building, Floor, Node, Zone
from app.repositories.building_repository import BuildingRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.sensor_type_repository import SensorTypeRepository
from app.repositories.zone_repository import ZoneRepository
from app.services.telemetry_service import TelemetryService
from tests.db.conftest import TEST_DATABASE_URL, areset_schema, run_alembic

PRE_FLOOR_REVISION = "b7e2c9a4d1f0"  # the migration before the floor table


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


async def new_building(client, name="Torre Norte") -> int:
    response = await client.post("/buildings", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["building_id"]


async def test_create_and_list_floors_of_a_building(api):
    client, _ = api
    building = await new_building(client)

    basement = await client.post("/floors", json={"building_id": building, "level": -1})
    ground = await client.post("/floors", json={"building_id": building, "level": 0})
    first = await client.post("/floors", json={"building_id": building, "level": 1, "name": "Primer piso"})

    assert [r.status_code for r in (basement, ground, first)] == [201, 201, 201]
    assert basement.json()["name"] == "Sótano 1"  # default names
    assert ground.json()["name"] == "Piso 0"
    assert first.json()["name"] == "Primer piso"

    # Out of order on purpose: the list must come back from the lowest level up.
    for url in (f"/buildings/{building}/floors", f"/floors/building/{building}"):
        listed = await client.get(url)
        assert listed.status_code == 200
        assert [f["level"] for f in listed.json()] == [-1, 0, 1]


async def test_a_building_cannot_have_two_floors_with_the_same_level(api):
    client, _ = api
    building = await new_building(client)
    await client.post("/floors", json={"building_id": building, "level": 1})

    duplicate = await client.post("/floors", json={"building_id": building, "level": 1})
    assert duplicate.status_code == 409

    other_building = await new_building(client, "Torre Sur")
    allowed = await client.post("/floors", json={"building_id": other_building, "level": 1})
    assert allowed.status_code == 201


async def test_floor_of_an_unknown_building_is_404(api):
    client, _ = api
    response = await client.post("/floors", json={"building_id": 999, "level": 1})
    assert response.status_code == 404


async def test_update_floor_name_and_level(api):
    client, _ = api
    building = await new_building(client)
    first = (await client.post("/floors", json={"building_id": building, "level": 1})).json()
    await client.post("/floors", json={"building_id": building, "level": 2})

    renamed = await client.patch(f"/floors/{first['floor_id']}", json={"name": "Oficinas"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Oficinas"

    taken = await client.patch(f"/floors/{first['floor_id']}", json={"level": 2})
    assert taken.status_code == 409


async def test_zone_uses_a_floor_of_its_own_building_only(api):
    client, _ = api
    north = await new_building(client)
    south = await new_building(client, "Torre Sur")
    north_floor = (await client.post("/floors", json={"building_id": north, "level": 1})).json()
    south_floor = (await client.post("/floors", json={"building_id": south, "level": 1})).json()

    ok = await client.post("/zones", json={"building_id": north, "name": "Recepción", "floor_id": north_floor["floor_id"]})
    assert ok.status_code == 201 and ok.json()["floor_id"] == north_floor["floor_id"]

    wrong = await client.post("/zones", json={"building_id": north, "name": "Mala", "floor_id": south_floor["floor_id"]})
    assert wrong.status_code == 422

    without = await client.post("/zones", json={"building_id": north, "name": "Patio"})
    assert without.status_code == 201 and without.json()["floor_id"] is None


async def test_cannot_delete_a_floor_with_zones_but_can_delete_an_empty_one(api):
    client, _ = api
    building = await new_building(client)
    used = (await client.post("/floors", json={"building_id": building, "level": 1})).json()
    empty = (await client.post("/floors", json={"building_id": building, "level": 2})).json()
    await client.post("/zones", json={"building_id": building, "name": "Recepción", "floor_id": used["floor_id"]})

    blocked = await client.delete(f"/floors/{used['floor_id']}")
    assert blocked.status_code == 409
    assert (await client.get(f"/floors/{used['floor_id']}")).status_code == 200  # still there

    deleted = await client.delete(f"/floors/{empty['floor_id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/floors/{empty['floor_id']}")).status_code == 404


async def test_the_database_itself_rejects_a_floor_of_another_building(api):
    """Not only the API: the composite foreign key (floor_id, building_id) stops it at the table."""
    _, s = api
    north, south = Building(name="Norte"), Building(name="Sur")
    s.add_all([north, south])
    await s.flush()
    floor = Floor(building_id=north.building_id, level=1, name="Piso 1")
    s.add(floor)
    await s.flush()

    s.add(Zone(building_id=south.building_id, name="Zona", floor_id=floor.floor_id))
    with pytest.raises(IntegrityError):
        await s.flush()
    await s.rollback()


async def test_migration_turns_zone_floor_numbers_into_floors():
    """Existing zones keep their floor: one floor per (building, number), named by its level."""
    await areset_schema()
    assert run_alembic("downgrade", PRE_FLOOR_REVISION).returncode == 0

    conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
    await conn.execute("INSERT INTO building (name) VALUES ('A'), ('B')")
    await conn.execute(
        "INSERT INTO zone (building_id, name, floor) VALUES "
        "(1,'z1',1),(1,'z2',1),(1,'z3',0),(1,'z4',-1),(1,'z5',NULL),(2,'z6',1)"
    )
    await conn.close()

    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
    floors = await conn.fetch("SELECT building_id, level, name FROM floor ORDER BY building_id, level")
    zones = await conn.fetch(
        "SELECT z.name, f.building_id AS fb, f.level FROM zone z LEFT JOIN floor f USING (floor_id) ORDER BY z.zone_id"
    )
    await conn.close()

    assert [(f["building_id"], f["level"], f["name"]) for f in floors] == [
        (1, -1, "Sótano 1"), (1, 0, "Planta baja"), (1, 1, "Piso 1"), (2, 1, "Piso 1"),
    ]
    # z1 and z2 share one floor; z5 had no floor and stays without one; z6 is in the other building.
    assert [(z["name"], z["fb"], z["level"]) for z in zones] == [
        ("z1", 1, 1), ("z2", 1, 1), ("z3", 1, 0), ("z4", 1, -1), ("z5", None, None), ("z6", 2, 1),
    ]


async def test_telemetry_by_node_reports_the_floor_of_its_zone(api):
    _, s = api
    building = Building(name="Norte")
    s.add(building)
    await s.flush()
    floor = Floor(building_id=building.building_id, level=-1, name="Sótano 1")
    s.add(floor)
    await s.flush()
    zone = Zone(building_id=building.building_id, name="Parqueadero", floor_id=floor.floor_id)
    s.add(zone)
    await s.flush()
    node = Node(code="NODE-B1", name="Bridge sótano", zone_id=zone.zone_id)
    s.add(node)
    await s.flush()

    service = TelemetryService(BuildingRepository(s), ZoneRepository(s), NodeRepository(s), SensorRepository(s),
                               SensorTypeRepository(s), ReadingRepository(s))
    data = await service.get_telemetry_by_node(node.node_id)

    assert data["zone"]["floor"] == -1
    assert data["zone"]["floor_name"] == "Sótano 1"
