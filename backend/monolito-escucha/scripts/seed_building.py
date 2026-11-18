"""Siembra un edificio con sus pisos y zonas para poder registrar los nodos.

El registro de un nodo pide `building_id` y `zone_id` (POST /registrations en consulta): sin al
menos un edificio y una zona, la solicitud responde 404. Esta seed crea el edificio de demo de la
simulación (Sentinel Building, SB-001) con dos pisos y una zona por piso, que son los nodos
NODE-FLOOR-1 y NODE-FLOOR-2 del simulador.

Es idempotente: lo que ya existe (mismo nombre de edificio, mismo nivel de piso, misma zona en el
edificio) se deja como está, así que se puede ejecutar varias veces. Imprime los ids que se
escriben en el formulario de registro.

Uso, dentro del contenedor de escucha:

    docker compose exec monolito-escucha python -m scripts.seed_building
    docker compose exec monolito-escucha python -m scripts.seed_building --building "Mi edificio" --floors 3
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def seed(building_name: str, address: str | None, floors: int) -> list[dict]:
    engine = create_async_engine(settings.database_url)
    rows: list[dict] = []
    try:
        async with engine.begin() as con:  # una sola transacción: o se siembra todo o nada
            building_id = (await con.execute(
                text("SELECT building_id FROM building WHERE name = :name ORDER BY building_id LIMIT 1"),
                {"name": building_name},
            )).scalar()
            created_building = building_id is None
            if created_building:
                building_id = (await con.execute(
                    text("INSERT INTO building (name, address) VALUES (:name, :address) RETURNING building_id"),
                    {"name": building_name, "address": address},
                )).scalar_one()

            for level in range(1, floors + 1):
                floor_id = (await con.execute(
                    text("SELECT floor_id FROM floor WHERE building_id = :b AND level = :l"),
                    {"b": building_id, "l": level},
                )).scalar()
                if floor_id is None:
                    floor_id = (await con.execute(
                        text("INSERT INTO floor (building_id, level, name) VALUES (:b, :l, :n) RETURNING floor_id"),
                        {"b": building_id, "l": level, "n": f"Piso {level}"},
                    )).scalar_one()

                zone_name = f"Zona piso {level}"
                zone_id = (await con.execute(
                    text("SELECT zone_id FROM zone WHERE building_id = :b AND name = :n ORDER BY zone_id LIMIT 1"),
                    {"b": building_id, "n": zone_name},
                )).scalar()
                created_zone = zone_id is None
                if created_zone:
                    zone_id = (await con.execute(
                        text("INSERT INTO zone (building_id, name, floor_id) VALUES (:b, :n, :f) RETURNING zone_id"),
                        {"b": building_id, "n": zone_name, "f": floor_id},
                    )).scalar_one()
                rows.append({"building_id": building_id, "floor": level, "zone_id": zone_id,
                             "zone": zone_name, "new": created_building or created_zone})
    finally:
        await engine.dispose()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra un edificio, sus pisos y una zona por piso")
    parser.add_argument("--building", default="Sentinel Building", help="nombre del edificio")
    parser.add_argument("--address", default=None, help="dirección (opcional)")
    parser.add_argument("--floors", type=int, default=2, help="cantidad de pisos (una zona por piso)")
    args = parser.parse_args()
    if args.floors < 1:
        parser.error("--floors debe ser al menos 1")

    rows = asyncio.run(seed(args.building, args.address, args.floors))
    print(f"Edificio «{args.building}»")
    print(f"{'building_id':>12} {'piso':>5} {'zone_id':>8}  zona")
    for row in rows:
        print(f"{row['building_id']:>12} {row['floor']:>5} {row['zone_id']:>8}  {row['zone']}"
              f"{'' if row['new'] else '  (ya existía)'}")


if __name__ == "__main__":
    main()
