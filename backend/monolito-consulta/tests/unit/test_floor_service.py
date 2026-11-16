"""Pisos: nombre por omisión, nivel único por edificio, borrado con zonas y piso de la zona (sin base de datos)."""
from types import SimpleNamespace

import pytest

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableEntityError
from app.schemas.floor import FloorCreate, FloorUpdate
from app.schemas.zone import ZoneCreate, ZoneUpdate
from app.services.floor_service import FloorService, default_floor_name
from app.services.zone_service import ZoneService


class FakeFloors:
    def __init__(self):
        self.rows: dict[int, SimpleNamespace] = {}
        self.zone_counts: dict[int, int] = {}
        self._next = 1

    async def get(self, floor_id):
        return self.rows.get(floor_id)

    async def get_by_building(self, building_id):
        return sorted((f for f in self.rows.values() if f.building_id == building_id), key=lambda f: f.level)

    async def get_by_building_and_level(self, building_id, level):
        return next((f for f in self.rows.values() if f.building_id == building_id and f.level == level), None)

    async def count_zones(self, floor_id):
        return self.zone_counts.get(floor_id, 0)

    async def create(self, data):
        floor = SimpleNamespace(floor_id=self._next, **data)
        self.rows[self._next] = floor
        self._next += 1
        return floor

    async def update(self, floor, floor_in):
        for key, value in floor_in.model_dump(exclude_unset=True).items():
            setattr(floor, key, value)
        return floor

    async def delete(self, floor_id):
        return self.rows.pop(floor_id, None) is not None


class FakeBuildings:
    def __init__(self, *ids):
        self.ids = set(ids)

    async def get(self, building_id):
        return SimpleNamespace(building_id=building_id) if building_id in self.ids else None


class FakeZones:
    def __init__(self):
        self.rows: dict[int, SimpleNamespace] = {}
        self._next = 1

    async def get(self, zone_id):
        return self.rows.get(zone_id)

    async def create(self, zone_in):
        zone = SimpleNamespace(zone_id=self._next, **zone_in.model_dump())
        self.rows[self._next] = zone
        self._next += 1
        return zone

    async def update(self, zone, zone_in):
        for key, value in zone_in.model_dump(exclude_unset=True).items():
            setattr(zone, key, value)
        return zone


@pytest.fixture
def floors():
    return FakeFloors()


@pytest.fixture
def service(floors):
    return FloorService(floors, FakeBuildings(1, 2))


def test_default_names():
    assert default_floor_name(0) == "Piso 0"
    assert default_floor_name(-1) == "Sótano 1"
    assert default_floor_name(-2) == "Sótano 2"
    assert default_floor_name(3) == "Piso 3"


async def test_create_without_name_uses_the_default_name(service):
    floor = await service.create(FloorCreate(building_id=1, level=-1))
    assert (floor.level, floor.name) == (-1, "Sótano 1")


async def test_create_keeps_the_given_name(service):
    floor = await service.create(FloorCreate(building_id=1, level=0, name="Lobby"))
    assert floor.name == "Lobby"


async def test_create_in_an_unknown_building_is_404(service):
    with pytest.raises(NotFoundError):
        await service.create(FloorCreate(building_id=99, level=1))


async def test_two_floors_with_the_same_level_in_one_building_conflict(service):
    await service.create(FloorCreate(building_id=1, level=1))
    with pytest.raises(ConflictError):
        await service.create(FloorCreate(building_id=1, level=1))


async def test_the_same_level_is_allowed_in_another_building(service):
    await service.create(FloorCreate(building_id=1, level=1))
    other = await service.create(FloorCreate(building_id=2, level=1))
    assert other.building_id == 2


async def test_floors_of_a_building_come_from_the_lowest_level_up(service):
    for level in (2, -1, 0):
        await service.create(FloorCreate(building_id=1, level=level))
    assert [f.level for f in await service.get_by_building(1)] == [-1, 0, 2]


async def test_floors_of_an_unknown_building_is_404(service):
    with pytest.raises(NotFoundError):
        await service.get_by_building(99)


async def test_update_to_a_taken_level_conflicts_but_keeping_the_level_does_not(service):
    await service.create(FloorCreate(building_id=1, level=1))
    second = await service.create(FloorCreate(building_id=1, level=2))

    with pytest.raises(ConflictError):
        await service.update(second.floor_id, FloorUpdate(level=1))

    renamed = await service.update(second.floor_id, FloorUpdate(level=2, name="Oficinas"))
    assert renamed.name == "Oficinas"


async def test_delete_is_blocked_while_the_floor_has_zones(service, floors):
    floor = await service.create(FloorCreate(building_id=1, level=1))
    floors.zone_counts[floor.floor_id] = 2

    with pytest.raises(ConflictError):
        await service.delete(floor.floor_id)
    assert floor.floor_id in floors.rows  # nothing was deleted


async def test_delete_an_empty_floor(service, floors):
    floor = await service.create(FloorCreate(building_id=1, level=1))
    await service.delete(floor.floor_id)
    assert floor.floor_id not in floors.rows


async def test_delete_unknown_floor_is_404(service):
    with pytest.raises(NotFoundError):
        await service.delete(123)


# --- the floor of a zone must belong to the zone's building ---

@pytest.fixture
async def zone_service(floors):
    await FloorService(floors, FakeBuildings(1, 2)).create(FloorCreate(building_id=1, level=1))  # floor 1 -> building 1
    await FloorService(floors, FakeBuildings(1, 2)).create(FloorCreate(building_id=2, level=1))  # floor 2 -> building 2
    return ZoneService(FakeZones(), floors)


async def test_zone_with_a_floor_of_its_own_building(zone_service):
    zone = await zone_service.create(ZoneCreate(building_id=1, name="Recepción", floor_id=1))
    assert zone.floor_id == 1


async def test_zone_without_floor_is_allowed(zone_service):
    zone = await zone_service.create(ZoneCreate(building_id=1, name="Patio"))
    assert zone.floor_id is None


async def test_zone_with_a_floor_of_another_building_is_422(zone_service):
    with pytest.raises(UnprocessableEntityError):
        await zone_service.create(ZoneCreate(building_id=1, name="Mala", floor_id=2))


async def test_zone_with_an_unknown_floor_is_404(zone_service):
    with pytest.raises(NotFoundError):
        await zone_service.create(ZoneCreate(building_id=1, name="Mala", floor_id=99))


async def test_moving_a_zone_to_another_building_without_changing_its_floor_is_422(zone_service):
    zone = await zone_service.create(ZoneCreate(building_id=1, name="Recepción", floor_id=1))
    with pytest.raises(UnprocessableEntityError):
        await zone_service.update(zone.zone_id, ZoneUpdate(building_id=2))


async def test_a_zone_can_clear_its_floor(zone_service):
    zone = await zone_service.create(ZoneCreate(building_id=1, name="Recepción", floor_id=1))
    updated = await zone_service.update(zone.zone_id, ZoneUpdate(floor_id=None))
    assert updated.floor_id is None


async def test_changing_only_the_name_keeps_the_floor(zone_service):
    zone = await zone_service.create(ZoneCreate(building_id=1, name="Recepción", floor_id=1))
    updated = await zone_service.update(zone.zone_id, ZoneUpdate(name="Entrada"))
    assert (updated.name, updated.floor_id) == ("Entrada", 1)
