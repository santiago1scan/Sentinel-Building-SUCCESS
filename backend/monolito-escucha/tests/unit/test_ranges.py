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
    # Excel pressure is sea-level (1013-1024 hPa); Popayan measures about 825 hPa.
    assert (DEFAULT_RANGES["pressure_hpa"].normal_minimum, DEFAULT_RANGES["pressure_hpa"].normal_maximum) == (815, 835)


def test_team_ranges_judge_the_node_readings():
    """Ranges the team passed on 16-Nov-2026 for the thermal camera, TVOC, vibration and power."""
    assert evaluate(1, DEFAULT_RANGES["hot_pixels"]) == "above"  # normal max is 0 hot pixels
    assert evaluate(0, DEFAULT_RANGES["hot_pixels"]) == "normal"
    assert evaluate(100, DEFAULT_RANGES["tvoc_ppb"]) == "normal"  # 0.1 ppm: cleaner air, not an alarm
    assert evaluate(900, DEFAULT_RANGES["tvoc_ppb"]) == "above"
    assert evaluate(10.5, DEFAULT_RANGES["bus_voltage_v"]) == "below"
    assert evaluate(7000, DEFAULT_RANGES["power_mw"]) == "above"
    assert evaluate(2.5, DEFAULT_RANGES["frequency_hz"]) == "below"
    # Zero-width range: counted in pixels, so a hot camera does not rank last among open alerts.
    assert deviation(3, DEFAULT_RANGES["hot_pixels"]) == 3


def test_iaq_below_51_is_cleaner_air_not_an_alarm():
    assert evaluate(30, IAQ) == "normal"


def test_iaq_300_is_above():
    assert evaluate(300, IAQ) == "above"


def test_temperature_below_range_is_below():
    assert evaluate(5, TEMPERATURE) == "below"


def test_humidity_150_is_impossible_not_above():
    assert evaluate(150, HUMIDITY) == "impossible"


def test_popayan_pressure_is_normal_and_sea_level_is_above():
    assert evaluate(825, DEFAULT_RANGES["pressure_hpa"]) == "normal"
    assert evaluate(1013, DEFAULT_RANGES["pressure_hpa"]) == "above"


def test_edges_are_normal():
    assert evaluate(31, TEMPERATURE) == "normal"
    assert evaluate(10, TEMPERATURE) == "normal"


def test_deviation_is_distance_over_range_width():
    assert deviation(40, TEMPERATURE) == (40 - 31) / (31 - 10)
    assert deviation(5, TEMPERATURE) == (10 - 5) / (31 - 10)
    assert deviation(20, TEMPERATURE) == 0
    assert deviation(20, Range()) == 0
