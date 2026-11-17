"""Normal and physical ranges per variable, and how a value is judged against them.

Defaults come from Parametros_Normales_Cauca_Colombia.xlsx (sheet Umbrales_Normales, Popayan 2026) and, for the
thermal camera, TVOC, vibration and power, from the team (16-Nov-2026). They are only
used when a variable is first seen; after that the database row (sensor_metric) is the source of truth.
"""
from dataclasses import dataclass
from typing import Literal, Protocol

Status = Literal["normal", "above", "below", "impossible", "no_range"]


class RangeLike(Protocol):
    normal_minimum: float | None
    normal_maximum: float | None
    physical_minimum: float | None
    physical_maximum: float | None
    alarm_below: bool
    alarm_above: bool


@dataclass(frozen=True)
class Range:
    normal_minimum: float | None = None
    normal_maximum: float | None = None
    physical_minimum: float | None = None
    physical_maximum: float | None = None
    alarm_below: bool = True
    alarm_above: bool = True
    unit: str | None = None


DEFAULT_RANGES: dict[str, Range] = {
    # BME688
    "temperature_c": Range(10, 31, -40, 85, unit="°C"),
    "humidity_percent": Range(72.78, 94.48, 0, 100, unit="%"),
    # The Excel range (1013.7-1024 hPa) is sea-level pressure; at ~1,740 m Popayan reads ~0.811 of it (822-831 hPa).
    # 815-835 hPa with a margin: an estimate until it is measured on site (17-Nov-2026).
    "pressure_hpa": Range(815, 835, 300, 1100, unit="hPa"),
    # IAQ below 51 is "Excellent" air (Bosch table 6): out of range, but not an alarm.
    "iaq_index": Range(51, 100, 0, 500, alarm_below=False, unit="IAQ"),
    # ADXL355: project proposal, below MMI IV (0.0276 g), Worden et al. (2012)
    "x_g": Range(-0.01, 0.01, unit="g"),
    "y_g": Range(-0.01, 0.01, unit="g"),
    "z_g": Range(0.99, 1.01, unit="g"),
    # Team ranges, 16-Nov-2026 (thermal camera, gases, vibration, power).
    "rms_g": Range(0.0002, 0.0071, unit="g"),
    "frequency_hz": Range(3, 4, unit="Hz"),
    "maximum_c": Range(17, 35, unit="°C"),
    "average_c": Range(17, 26, unit="°C"),
    "hot_pixels": Range(0, 0, unit="píxeles"),
    # 0.3-0.5 ppm, in ppb as the BME688 sends it; below 0.3 ppm is cleaner air, not an alarm (same as IAQ).
    "tvoc_ppb": Range(300, 500, alarm_below=False, unit="ppb"),
    "bus_voltage_v": Range(11, 12, unit="V"),
    "current_ma": Range(300, 500, unit="mA"),
    "power_mw": Range(3300, 6000, unit="mW"),
    # 0/1 flags, normal = 0. They raise their own technical notice and are never judged against this range.
    "power_source": Range(0, 0, 0, 1),
    "battery_low": Range(0, 0, 0, 1),
}


def _f(value) -> float | None:
    return None if value is None else float(value)


def evaluate(value: float, r: RangeLike) -> Status:
    if (_f(r.physical_minimum) is not None and value < _f(r.physical_minimum)) or (
        _f(r.physical_maximum) is not None and value > _f(r.physical_maximum)
    ):
        return "impossible"
    low, high = _f(r.normal_minimum), _f(r.normal_maximum)
    if low is None and high is None:
        return "no_range"
    if high is not None and value > high:
        return "above" if r.alarm_above else "normal"
    if low is not None and value < low:
        return "below" if r.alarm_below else "normal"
    return "normal"


def deviation(value: float, r: RangeLike) -> float:
    """How far outside the normal range, in widths of the range (0 when inside or without a full range).

    A zero-width range (hot_pixels 0-0) is measured in units of the value, at least 1: 3 hot pixels = 3. Otherwise
    a hot thermal camera would rank last among open alerts.
    """
    low, high = _f(r.normal_minimum), _f(r.normal_maximum)
    if low is None or high is None or high < low:
        return 0
    width = high - low if high > low else max(abs(high), 1)
    if value > high:
        return (value - high) / width
    if value < low:
        return (low - value) / width
    return 0
