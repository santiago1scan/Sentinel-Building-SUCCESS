"""Severity of out-of-range alerts: emergencia or leve (rule approved on 24-Nov-2026).

The system still does not say what is happening (a candle, a fire): it grades how serious the node looks, from the
out-of-range alerts that are open on that node right now.
- Emergency: any motion or energy alert, or temperature and air quality at the same time (heat plus smoke/gases).
- Minor: anything else, i.e. only heat (a candle) or only air quality (perfume, a cleaner).
Technical notices (damaged sensor, battery, silence) never get a severity.

The categories are the panel's (frontend/src/features/nodes/alertGroups.js). A variable with no category is ignored.
"""
from collections.abc import Iterable

EMERGENCIA = "emergencia"
LEVE = "leve"

METRIC_CATEGORY: dict[str, str] = {
    "maximum_c": "temperature", "average_c": "temperature", "hot_pixels": "temperature",
    "temperature_c": "temperature",
    "humidity_percent": "air", "pressure_hpa": "air", "iaq_index": "air", "tvoc_ppb": "air",
    "x_g": "motion", "y_g": "motion", "z_g": "motion", "rms_g": "motion", "frequency_hz": "motion",
    "bus_voltage_v": "energy", "current_ma": "energy", "power_mw": "energy", "power_source": "energy",
    "battery_low": "energy",
}

_ALWAYS_EMERGENCY = {"motion", "energy"}


def classify_node(metric_codes: Iterable[str]) -> str | None:
    """Severity of a node from the variables of its open out-of-range alerts; None if none has a category."""
    categories = {METRIC_CATEGORY[code] for code in metric_codes if code in METRIC_CATEGORY}
    if not categories:
        return None
    if categories & _ALWAYS_EMERGENCY or {"temperature", "air"} <= categories:
        return EMERGENCIA
    return LEVE
