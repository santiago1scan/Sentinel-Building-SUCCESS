"""floor table: a floor is a row of its own, and zones point to it

Before, the floor was a bare integer on zone (zone.floor): no name, no guarantee it was not repeated.
Now building -> floor -> zone -> node:
- floor: one row per floor of a building. `level` is the number (-1 basement, 0 ground floor, 1 first...)
  and `name` is what people read. A building cannot have two floors with the same level.
- zone.floor_id replaces zone.floor. The foreign key is composite (floor_id, building_id), so a zone can
  only use a floor of its own building; the database enforces it, not only the API.
- Nodes keep zone_id; they reach their floor through their zone.

DATA: upgrade creates one floor per distinct (building, zone.floor) and links the zones to it, with the name
"Planta baja", "Sótano N" or "Piso N". Zones without a floor stay without one. downgrade writes the level back
into zone.floor (names are lost).

Revision ID: d5a9e3b1c7f2
Revises: b7e2c9a4d1f0
Create Date: 2026-11-16 15:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5a9e3b1c7f2"
down_revision: Union[str, Sequence[str], None] = "b7e2c9a4d1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "floor",
        sa.Column("floor_id", sa.BigInteger(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
        sa.Column("building_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["building.building_id"], name="fk_floor_building", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("floor_id", name="floor_pkey"),
        sa.UniqueConstraint("building_id", "level", name="uq_floor_building_level"),
        sa.UniqueConstraint("floor_id", "building_id", name="uq_floor_id_building"),
    )
    op.create_index("idx_floor_building", "floor", ["building_id"], unique=False)

    op.add_column("zone", sa.Column("floor_id", sa.BigInteger(), nullable=True))

    # One floor per distinct (building, number) already used by a zone, then link each zone to its floor.
    op.execute("""
        INSERT INTO floor (building_id, level, name)
        SELECT DISTINCT building_id, floor,
               CASE WHEN floor = 0 THEN 'Planta baja'
                    WHEN floor < 0 THEN 'Sótano ' || (-floor)::text
                    ELSE 'Piso ' || floor::text END
        FROM zone
        WHERE floor IS NOT NULL
    """)
    op.execute("""
        UPDATE zone SET floor_id = f.floor_id
        FROM floor f
        WHERE f.building_id = zone.building_id AND f.level = zone.floor
    """)

    op.create_foreign_key(
        "fk_zone_floor_building", "zone", "floor",
        ["floor_id", "building_id"], ["floor_id", "building_id"],
        onupdate="CASCADE", ondelete="RESTRICT",
    )
    op.drop_column("zone", "floor")


def downgrade() -> None:
    op.add_column("zone", sa.Column("floor", sa.Integer(), nullable=True))
    op.execute("UPDATE zone SET floor = f.level FROM floor f WHERE f.floor_id = zone.floor_id")
    op.drop_constraint("fk_zone_floor_building", "zone", type_="foreignkey")
    op.drop_column("zone", "floor_id")
    op.drop_index("idx_floor_building", table_name="floor")
    op.drop_table("floor")
