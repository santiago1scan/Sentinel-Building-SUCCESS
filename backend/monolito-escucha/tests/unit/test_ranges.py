"""Range evaluation: normal, above, below, impossible, no range. Values from the Umbrales_Normales sheet."""
from app.analytics.ranges import DEFAULT_RANGES, Range, deviation, evaluate

IAQ = DEFAULT_RANGES["iaq_index"]
HUMIDITY = DEFAULT_RANGES["humidity_percent"]
TEMPERATURE = DEFAULT_RANGES["temperature_c"]


def test_defaults_come_from_the_excel():
    assert (TEMPERATURE.normal_minimum, TEMPERATURE.normal_maximum) == (10, 31)
    assert (HUMIDITY.normal_minimum, HUMIDITY.normal_maximum) == (72.78, 94.48)
    assert (IAQ.normal_minimum, IAQ.normal_maximum, IAQ.alarm_below) == (51, 100, False)
    assert (DEFAULT_RANGES["z_g"].normal_minimum, DEFAULT_RANGES["z_g"].normal_maximum) == (0.99, 1.01)
    # Excel pressure is sea-level (1013-1024 hPa); Popayan measures about 825 hPa, so no normal range.
    assert DEFAULT_RANGES["pressure_hpa"].normal_minimum is None


def test_iaq_below_51_is_cleaner_air_not_an_alarm():
    assert evaluate(30, IAQ) == "normal"


def test_iaq_300_is_above():
    assert evaluate(300, IAQ) == "above"


def test_temperature_below_range_is_below():
    assert evaluate(5, TEMPERATURE) == "below"


def test_humidity_150_is_impossible_not_above():
    assert evaluate(150, HUMIDITY) == "impossible"


def test_pressure_825_has_no_range():
    assert evaluate(825, DEFAULT_RANGES["pressure_hpa"]) == "no_range"


def test_edges_are_normal():
    assert evaluate(31, TEMPERATURE) == "normal"
    assert evaluate(10, TEMPERATURE) == "normal"


def test_deviation_is_distance_over_range_width():
    assert deviation(40, TEMPERATURE) == (40 - 31) / (31 - 10)
    assert deviation(5, TEMPERATURE) == (10 - 5) / (31 - 10)
    assert deviation(20, TEMPERATURE) == 0
    assert deviation(20, Range()) == 0
