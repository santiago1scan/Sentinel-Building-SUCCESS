"""Semilla de prueba: un edificio con dos pisos y dos zonas, sin nodos ni sensores.

Las zonas y pisos siguen el catálogo del simulador (NODE-FLOOR-1 → ZONE-F1 piso 1,
NODE-FLOOR-2 → ZONE-F2 piso 2). Los nodos se registran después, con su token.

Es idempotente: si el edificio, los pisos o las zonas ya existen, no los duplica.

Uso (desde backend/monolito-consulta, con DATABASE_URL):
    python -m app.scripts.seed_edificio_prueba
"""
import asyncio

from sqlalchemy import select

from app.core.database import get_db_context
from app.models import Building, Floor, Zone

BUILDING_NAME = "Edificio de prueba SB-001"
BUILDING_ADDRESS = "Sede de prueba (simulador)"
FLOORS = [(1, "Piso 1"), (2, "Piso 2")]
ZONES = [("ZONE-F1", 1), ("ZONE-F2", 2)]  # (nombre de zona, nivel del piso)


async def seed() -> None:
    async with get_db_context() as session:
        building = (await session.execute(
            select(Building).where(Building.name == BUILDING_NAME)
        )).scalar_one_or_none()
        if building is None:
            building = Building(name=BUILDING_NAME, address=BUILDING_ADDRESS)
            session.add(building)
            await session.flush()
            print(f"edificio creado: {building.building_id} {BUILDING_NAME}")
        else:
            print(f"edificio existente: {building.building_id} {BUILDING_NAME}")

        floors: dict[int, Floor] = {}
        for level, name in FLOORS:
            floor = (await session.execute(
                select(Floor).where(Floor.building_id == building.building_id, Floor.level == level)
            )).scalar_one_or_none()
            if floor is None:
                floor = Floor(building_id=building.building_id, level=level, name=name)
                session.add(floor)
                await session.flush()
                print(f"piso creado: nivel {level} ({name})")
            floors[level] = floor

        for zone_name, level in ZONES:
            zone = (await session.execute(
                select(Zone).where(Zone.building_id == building.building_id, Zone.name == zone_name)
            )).scalar_one_or_none()
            if zone is None:
                session.add(Zone(
                    building_id=building.building_id,
                    name=zone_name,
                    floor_id=floors[level].floor_id,
                ))
                print(f"zona creada: {zone_name} en piso {level}")
            else:
                print(f"zona existente: {zone_name}")

        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
