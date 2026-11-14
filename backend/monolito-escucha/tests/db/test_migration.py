"""Migration to the 26-Oct database structure (sensor_metric, ingest_message, reading per metric)."""
import asyncio

import asyncpg

from tests.db.conftest import TEST_DATABASE_URL, reset_schema, run_alembic


async def _columns(table: str) -> set[str]:
    conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name = $1", table
    )
    await conn.close()
    return {r["column_name"] for r in rows}


def test_upgrade_and_downgrade_round_trip():
    reset_schema()

    assert {"metric_id", "sensor_type_id", "metric_code", "normal_minimum", "normal_maximum",
            "physical_minimum", "physical_maximum", "alarm_below", "alarm_above"} <= asyncio.run(_columns("sensor_metric"))
    assert {"message_id", "message_uid", "message_type", "generated_at", "window_start",
            "window_end"} <= asyncio.run(_columns("ingest_message"))
    assert {"message_id", "metric_id", "aggregation", "sample_count_sensor", "alert_id",
            "measured_at", "measured_value", "receiving_node_id"} <= asyncio.run(_columns("reading"))
    assert {"alert_type", "direction", "node_id", "sensor_id", "metric_id", "started_at",
            "last_seen_at", "ended_at", "peak_value", "deviation", "reading_count",
            "handled_at"} <= asyncio.run(_columns("alert"))

    down = run_alembic("downgrade", "-1")
    assert down.returncode == 0, down.stderr
    assert asyncio.run(_columns("sensor_metric")) == set()
    assert "aggregation" not in asyncio.run(_columns("reading"))

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr


def test_models_match_migrated_schema():
    """Every column a model declares exists in the migrated database (the two drifted once)."""
    import app.models as models

    reset_schema()
    for table in models.Base.metadata.sorted_tables:
        declared = {c.name for c in table.columns}
        missing = declared - asyncio.run(_columns(table.name))
        assert not missing, f"{table.name}: {missing}"
