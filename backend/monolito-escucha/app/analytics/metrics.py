"""Read the values of one sensor from a message.

Incident (`out_of_range`): each key is the variable, e.g. {"temperature_c": 40} -> raw.
Half-hour summary: each key is `<variable>__avg|max|min`, e.g. {"temperature_c__max": 33}; booleans such as
`battery_low` travel without suffix and are stored as raw 0/1.
"""
from dataclasses import dataclass
from typing import Any

AGGREGATIONS = ("avg", "max", "min")
# Text values stored as 0/1 like battery_low (business rule, 14-Nov-2026): 1 = the node runs on battery.
TEXT_FLAGS = {"power_source": {"battery": 1.0, "main": 0.0}}
SEPARATOR = "__"


@dataclass(frozen=True)
class MetricValue:
    metric_code: str
    aggregation: str  # raw | avg | max | min
    value: float


def _split(key: str) -> tuple[str, str]:
    base, sep, suffix = key.rpartition(SEPARATOR)
    if sep and base and suffix in AGGREGATIONS:
        return base, suffix
    return key, "raw"


def parse_sensor_values(data: Any) -> list[MetricValue]:
    """Numeric and boolean values only; text, lists and None are ignored."""
    if not isinstance(data, dict):
        data = data.model_dump() if hasattr(data, "model_dump") else {}
    values = []
    for key, raw in data.items():
        if isinstance(raw, bool):
            number = 1.0 if raw else 0.0
        elif isinstance(raw, (int, float)):
            number = float(raw)
        elif isinstance(raw, str) and raw.lower() in TEXT_FLAGS.get(_split(key)[0], {}):
            number = TEXT_FLAGS[_split(key)[0]][raw.lower()]
        else:
            continue
        code, aggregation = _split(key)
        values.append(MetricValue(code, aggregation, number))
    return values
