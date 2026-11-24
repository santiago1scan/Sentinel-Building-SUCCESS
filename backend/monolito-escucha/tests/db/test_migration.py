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


BEFORE_ANALYTICS = "a1d3f0c7b2e4"  # revision just before the analytics migration
BEFORE_FLOOR = "b7e2c9a4d1f0"  # the analytics migration: the head before the floor table
# Explicit revisions, not "-1": a later migration (e4b7d2a9c3f1, 17-Nov) made "-1" stop undoing the seed.
BEFORE_CATALOG = "d5a9e3b1c7f2"  # the floor table: the revision just before the sensor catalog seed
BEFORE_SEVERITY = "e4b7d2a9c3f1"  # node code as a label: the revision just before alert.severity


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

    # Back to before the analytics migration (this also undoes the floor migration, which comes after it).
    down = run_alembic("downgrade", BEFORE_ANALYTICS)
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


def test_floor_table_replaces_the_zone_floor_number():
    reset_schema()

    assert {"floor_id", "building_id", "level", "name"} <= asyncio.run(_columns("floor"))
    zone = asyncio.run(_columns("zone"))
    assert "floor_id" in zone and "floor" not in zone

    down = run_alembic("downgrade", BEFORE_FLOOR)
    assert down.returncode == 0, down.stderr
    assert asyncio.run(_columns("floor")) == set()
    zone = asyncio.run(_columns("zone"))
    assert "floor" in zone and "floor_id" not in zone

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr


SEED = "c3f8a2d6b9e1"  # the sensor catalog seed


async def _fetch(sql: str, *args):
    conn = await asyncpg.connect(TEST_DATABASE_URL.replace("+asyncpg", ""))
    rows = await conn.fetch(sql, *args)
    await conn.close()
    return rows


def _catalog() -> dict[str, dict[str, tuple]]:
    rows = asyncio.run(_fetch(
        "SELECT t.name AS type, m.metric_code, m.normal_minimum, m.normal_maximum, m.alarm_below "
        "FROM sensor_type t LEFT JOIN sensor_metric m ON m.sensor_type_id = t.sensor_type_id"))
    catalog: dict[str, dict[str, tuple]] = {}
    for r in rows:
        metrics = catalog.setdefault(r["type"], {})
        if r["metric_code"]:
            low, high = r["normal_minimum"], r["normal_maximum"]
            metrics[r["metric_code"]] = (None if low is None else float(low), None if high is None else float(high),
                                         r["alarm_below"])
    return catalog


def test_sensor_catalog_is_seeded_with_a_range_for_all_18_metrics():
    """Case of 16-Nov-2026: sensor_type and sensor_metric were empty, so no sensor could be registered."""
    reset_schema()
    catalog = _catalog()

    assert set(catalog) == {"ADXL355", "AMG8833", "BME688", "INA219"}
    assert sum(len(m) for m in catalog.values()) == 18
    # The 6 ranges of Parametros_Normales_Cauca_Colombia.xlsx (sheet Umbrales_Normales).
    assert catalog["BME688"]["temperature_c"] == (10, 31, True)
    assert catalog["BME688"]["humidity_percent"] == (72.78, 94.48, True)
    assert catalog["BME688"]["iaq_index"] == (51, 100, False)  # below 51 is cleaner air, not an alarm
    assert catalog["ADXL355"]["x_g"] == (-0.01, 0.01, True)
    assert catalog["ADXL355"]["y_g"] == (-0.01, 0.01, True)
    assert catalog["ADXL355"]["z_g"] == (0.99, 1.01, True)
    # The 9 team ranges of 16-Nov-2026 (thermal camera, gases, vibration, power).
    assert catalog["ADXL355"]["rms_g"] == (0.0002, 0.0071, True)
    assert catalog["ADXL355"]["frequency_hz"] == (3, 4, True)
    assert catalog["AMG8833"]["maximum_c"] == (17, 35, True)
    assert catalog["AMG8833"]["average_c"] == (17, 26, True)
    assert catalog["AMG8833"]["hot_pixels"] == (0, 0, True)
    assert catalog["BME688"]["tvoc_ppb"] == (300, 500, False)  # 0.3-0.5 ppm; below is cleaner air, not an alarm
    assert catalog["INA219"]["bus_voltage_v"] == (11, 12, True)
    assert catalog["INA219"]["current_ma"] == (300, 500, True)
    assert catalog["INA219"]["power_mw"] == (3300, 6000, True)
    # Excel sea-level pressure taken to Popayan's altitude (~825 hPa), with a margin (17-Nov-2026).
    assert catalog["BME688"]["pressure_hpa"] == (815, 835, True)
    # 0/1 flags: normal is 0 (on mains, battery fine).
    assert catalog["INA219"]["power_source"] == (0, 0, True)
    assert catalog["INA219"]["battery_low"] == (0, 0, True)
    without_range = [code for metrics in catalog.values() for code, (low, high, _) in metrics.items()
                     if low is None and high is None]
    assert without_range == []


def test_sensor_catalog_seed_is_idempotent_and_downgrade_keeps_what_is_in_use():
    reset_schema()
    asyncio.run(_fetch(
        "WITH b AS (INSERT INTO building (name) VALUES ('Sentinel') RETURNING building_id), "
        "z AS (INSERT INTO zone (building_id, name) SELECT building_id, 'Z-1' FROM b RETURNING zone_id), "
        "n AS (INSERT INTO node (code, name, zone_id) SELECT 'NODE-1', 'Nodo 1', zone_id FROM z RETURNING node_id) "
        "INSERT INTO sensor (code, primary_node_id, sensor_type_id) "
        "SELECT 'ACC-1', node_id, (SELECT sensor_type_id FROM sensor_type WHERE name = 'ADXL355') FROM n"))

    down = run_alembic("downgrade", BEFORE_CATALOG)
    assert down.returncode == 0, down.stderr
    after_down = _catalog()
    assert set(after_down) == {"ADXL355"}  # a sensor uses it: the type stays, its unused metrics go

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert sum(len(m) for m in _catalog().values()) == 18  # the existing type is reused, nothing is duplicated


def test_sensor_catalog_matches_default_ranges_and_reads_every_30_s():
    """The seed and app/analytics/ranges.py must not drift: a metric is the same seeded or created on first sight."""
    from app.analytics.ranges import DEFAULT_RANGES

    reset_schema()
    rows = asyncio.run(_fetch(
        "SELECT m.metric_code, m.unit, m.normal_minimum, m.normal_maximum, m.physical_minimum, m.physical_maximum, "
        "m.alarm_below, m.alarm_above FROM sensor_metric m"))
    seeded = {r["metric_code"]: r for r in rows}

    def f(v):
        return None if v is None else float(v)

    for code, r in DEFAULT_RANGES.items():
        row = seeded[code]
        assert (f(row["normal_minimum"]), f(row["normal_maximum"]), f(row["physical_minimum"]),
                f(row["physical_maximum"]), row["alarm_below"], row["alarm_above"], row["unit"]) == (
            r.normal_minimum, r.normal_maximum, r.physical_minimum, r.physical_maximum, r.alarm_below,
            r.alarm_above, r.unit), code
    intervals = asyncio.run(_fetch("SELECT DISTINCT sampling_interval FROM sensor_type"))
    assert [r["sampling_interval"] for r in intervals] == [30]


def test_sensor_catalog_seed_leaves_an_existing_metric_untouched():
    reset_schema()
    down = run_alembic("downgrade", BEFORE_CATALOG)
    assert down.returncode == 0, down.stderr
    # A BME688 with temperature_c already there (e.g. created on first sight), with another range.
    asyncio.run(_fetch(
        "WITH t AS (INSERT INTO sensor_type (name, sampling_interval) VALUES ('BME688', 1) RETURNING sensor_type_id) "
        "INSERT INTO sensor_metric (sensor_type_id, metric_code, normal_minimum, normal_maximum) "
        "SELECT sensor_type_id, 'temperature_c', 15, 25 FROM t"))

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
    catalog = _catalog()
    assert catalog["BME688"]["temperature_c"][:2] == (15, 25)  # not overwritten
    assert len(catalog["BME688"]) == 5  # the missing ones were added
    interval = asyncio.run(_fetch("SELECT sampling_interval FROM sensor_type WHERE name = 'BME688'"))
    assert interval[0]["sampling_interval"] == 1


def test_alert_severity_column_round_trip():
    """alert.severity (24-Nov-2026): emergencia | leve | NULL. Old alerts stay NULL; downgrade removes it."""
    reset_schema()
    columns = asyncio.run(_fetch(
        "SELECT is_nullable FROM information_schema.columns WHERE table_name = 'alert' AND column_name = 'severity'"))
    assert [c["is_nullable"] for c in columns] == ["YES"]

    down = run_alembic("downgrade", BEFORE_SEVERITY)
    assert down.returncode == 0, down.stderr
    assert "severity" not in asyncio.run(_columns("alert"))
    asyncio.run(_fetch(
        "INSERT INTO alert (event_uuid, alert_code, alert_type, started_at, last_seen_at) "
        "VALUES ('old-1', 'NODE_SILENT', 'technical', now(), now())"))

    up = run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
    old = asyncio.run(_fetch("SELECT severity FROM alert WHERE event_uuid = 'old-1'"))
    assert [r["severity"] for r in old] == [None]  # an existing alert is kept, with no severity

    for value in ("emergencia", "leve"):
        asyncio.run(_fetch("UPDATE alert SET severity = $1 WHERE event_uuid = 'old-1'", value))
    try:
        asyncio.run(_fetch("UPDATE alert SET severity = 'grave' WHERE event_uuid = 'old-1'"))
        raise AssertionError("severity 'grave' should violate chk_alert_severity")
    except asyncpg.exceptions.CheckViolationError:
        pass
