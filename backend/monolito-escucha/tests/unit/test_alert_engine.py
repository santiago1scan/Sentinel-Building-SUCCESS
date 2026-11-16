"""Grouping out-of-range readings into one alert and technical notices, without a database.

Business rules (13-Nov-2026): an event ends when the incoming data is normal again; IAQ below 51 is not an alarm.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.alert_engine import AlertEngine
from app.analytics.ranges import DEFAULT_RANGES

T0 = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
SENSOR, NODE = 7, 3
pytestmark = pytest.mark.asyncio


@dataclass
class Metric:
    metric_id: int
    metric_code: str
    normal_minimum: float | None
    normal_maximum: float | None
    physical_minimum: float | None
    physical_maximum: float | None
    alarm_below: bool
    alarm_above: bool


def metric(code: str, metric_id: int) -> Metric:
    r = DEFAULT_RANGES.get(code)
    if r is None:
        return Metric(metric_id, code, None, None, None, None, True, True)
    return Metric(metric_id, code, r.normal_minimum, r.normal_maximum, r.physical_minimum,
                  r.physical_maximum, r.alarm_below, r.alarm_above)


TEMP = metric("temperature_c", 1)
IAQ = metric("iaq_index", 2)
HUM = metric("humidity_percent", 3)
BATTERY = metric("battery_low", 4)


class FakeStore:
    def __init__(self):
        self.alerts = []
        self.summaries: dict[tuple[int, int], list[tuple[float, float]]] = {}

    async def find_open(self, *, alert_type, alert_code, sensor_id=None, metric_id=None, node_id=None,
                        direction=None):
        for a in self.alerts:
            if (a.ended_at is None and a.alert_type == alert_type and a.alert_code == alert_code
                    and a.sensor_id == sensor_id and a.metric_id == metric_id and a.node_id == node_id
                    and a.direction == direction):
                return a
        return None

    async def open_out_of_range(self, sensor_id, metric_id):
        return [a for a in self.alerts if a.ended_at is None and a.alert_type == "out_of_range"
                and a.sensor_id == sensor_id and a.metric_id == metric_id]

    async def add(self, alert):
        alert.alert_id = len(self.alerts) + 1
        self.alerts.append(alert)
        return alert

    async def recent_summary_extremes(self, sensor_id, metric_id, limit):
        return self.summaries.get((sensor_id, metric_id), [])[-limit:][::-1]

    def summary(self, m, mx, mn):
        self.summaries.setdefault((SENSOR, m.metric_id), []).append((mx, mn))


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def engine(store):
    return AlertEngine(store)


def minutes(n):
    return T0 + timedelta(minutes=n)


async def test_three_high_readings_make_one_alert_with_count_and_peak(engine, store):
    for i, value in enumerate([35, 40, 38]):
        alert = await engine.on_raw(SENSOR, NODE, TEMP, value, minutes(i), reading_id=100 + i)
    assert len(store.alerts) == 1
    assert alert.reading_count == 3
    assert float(alert.peak_value) == 40
    assert alert.direction == "above"
    assert alert.alert_type == "out_of_range"
    assert alert.started_at == minutes(0) and alert.last_seen_at == minutes(2)
    assert alert.reading_id == 100
    assert float(alert.deviation) == pytest.approx((40 - 31) / 21, abs=1e-4)  # stored with 4 decimals, like the column


async def test_a_normal_reading_closes_it_and_a_new_high_opens_another(engine, store):
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(0), reading_id=1)
    assert await engine.on_raw(SENSOR, NODE, TEMP, 25, minutes(5), reading_id=2) is None
    assert store.alerts[0].ended_at == minutes(5)
    await engine.on_raw(SENSOR, NODE, TEMP, 36, minutes(9), reading_id=3)
    assert len(store.alerts) == 2 and store.alerts[1].ended_at is None


async def test_summary_with_max_and_min_in_range_closes(engine, store):
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(0), reading_id=1)
    store.summary(TEMP, 30, 20)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=25, max_=30, min_=20, window_end=minutes(30))
    assert store.alerts[0].ended_at == minutes(30)


async def test_summary_with_only_the_average_in_range_does_not_close(engine, store):
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(0), reading_id=1)
    store.summary(TEMP, 36, 20)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=25, max_=36, min_=20, window_end=minutes(30))
    assert store.alerts[0].ended_at is None


async def test_iaq_30_opens_nothing_and_iaq_300_opens(engine, store):
    assert await engine.on_raw(SENSOR, NODE, IAQ, 30, minutes(0), reading_id=1) is None
    assert store.alerts == []
    await engine.on_raw(SENSOR, NODE, IAQ, 300, minutes(1), reading_id=2)
    assert len(store.alerts) == 1 and store.alerts[0].direction == "above"


async def test_humidity_150_is_impossible_and_not_out_of_range(engine, store):
    alert = await engine.on_raw(SENSOR, NODE, HUM, 150, minutes(0), reading_id=1)
    assert alert.alert_type == "technical" and alert.alert_code == "SENSOR_IMPOSSIBLE"
    assert [a.alert_type for a in store.alerts] == ["technical"]


async def test_sensor_stuck_after_four_flat_summaries_and_cleared_when_it_moves(engine, store):
    for i in range(3):
        store.summary(TEMP, 22, 22)
        await engine.on_summary(SENSOR, NODE, TEMP, avg=22, max_=22, min_=22, window_end=minutes(30 * i))
    assert store.alerts == []
    store.summary(TEMP, 22, 22)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=22, max_=22, min_=22, window_end=minutes(90))
    assert [a.alert_code for a in store.alerts] == ["SENSOR_STUCK"]
    store.summary(TEMP, 23, 21)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=22, max_=23, min_=21, window_end=minutes(120))
    assert store.alerts[0].ended_at == minutes(120)


async def test_battery_low_opens_and_closes(engine, store):
    await engine.on_battery(NODE, SENSOR, BATTERY, 1, minutes(30))
    await engine.on_battery(NODE, SENSOR, BATTERY, 1, minutes(60))
    assert len(store.alerts) == 1
    assert store.alerts[0].alert_code == "BATTERY_LOW" and store.alerts[0].alert_type == "technical"
    await engine.on_battery(NODE, SENSOR, BATTERY, 0, minutes(90))
    assert store.alerts[0].ended_at == minutes(90)


async def test_node_heard_closes_node_silent(engine, store):
    await engine.open_node_silent(NODE, minutes(36))
    await engine.open_node_silent(NODE, minutes(41))
    assert len(store.alerts) == 1
    await engine.on_node_heard(NODE, minutes(50))
    assert store.alerts[0].ended_at == minutes(50)


async def test_late_summary_does_not_close_a_later_alert(engine, store):
    """Review D3: the bridge outbox retries; a 10:00-10:30 summary arriving after a 10:35 incident must not close it."""
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(35), reading_id=1)
    store.summary(TEMP, 30, 20)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=25, max_=30, min_=20, window_end=minutes(30))
    assert store.alerts[0].ended_at is None


async def test_late_normal_reading_does_not_close_a_later_alert(engine, store):
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(35), reading_id=1)
    await engine.on_raw(SENSOR, NODE, TEMP, 25, minutes(20), reading_id=2)
    assert store.alerts[0].ended_at is None


async def test_summary_with_only_max_does_not_close(engine, store):
    """Review D8: the rule needs max AND min in range."""
    await engine.on_raw(SENSOR, NODE, TEMP, 35, minutes(0), reading_id=1)
    await engine.on_summary(SENSOR, NODE, TEMP, avg=None, max_=30, min_=None, window_end=minutes(30))
    assert store.alerts[0].ended_at is None


async def test_on_battery_power_opens_and_closes(engine, store):
    power = metric("power_source", 5)
    await engine.on_battery(NODE, SENSOR, power, 1, minutes(0), code="ON_BATTERY_POWER")
    assert [(a.alert_code, a.alert_type) for a in store.alerts] == [("ON_BATTERY_POWER", "technical")]
    await engine.on_battery(NODE, SENSOR, power, 0, minutes(5), code="ON_BATTERY_POWER")
    assert store.alerts[0].ended_at == minutes(5)
