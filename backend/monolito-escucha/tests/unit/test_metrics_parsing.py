"""How the values of a sensor are read from a message (incident or half-hour summary)."""
from app.analytics.metrics import MetricValue, parse_sensor_values


def test_incident_value_is_raw():
    assert parse_sensor_values({"temperature_c": 40}) == [MetricValue("temperature_c", "raw", 40.0)]


def test_summary_keys_carry_their_aggregation():
    values = parse_sensor_values({"temperature_c__avg": 21.5, "temperature_c__max": 33, "temperature_c__min": 18})
    assert set(values) == {
        MetricValue("temperature_c", "avg", 21.5),
        MetricValue("temperature_c", "max", 33.0),
        MetricValue("temperature_c", "min", 18.0),
    }


def test_booleans_are_stored_as_zero_or_one():
    assert parse_sensor_values({"battery_low": True}) == [MetricValue("battery_low", "raw", 1.0)]
    assert parse_sensor_values({"battery_low": False}) == [MetricValue("battery_low", "raw", 0.0)]


def test_non_numeric_values_are_ignored():
    data = {"matrix_size": "8x8", "pixels_c": [[1, 2]], "status": "ok", "iaq_index": 300, "x": None}
    assert parse_sensor_values(data) == [MetricValue("iaq_index", "raw", 300.0)]


def test_unknown_suffix_is_kept_as_part_of_the_code():
    assert parse_sensor_values({"rms_g__p95": 0.2}) == [MetricValue("rms_g__p95", "raw", 0.2)]


def test_sensor_dto_keeps_every_key_of_data():
    """Real case (13-Nov-2026): the typed union turned every payload into TemperatureSensorData and dropped
    keys such as temperature_c__avg, so nothing was stored."""
    from app.services.DTOS.telemetry_dto import SensorDTO

    dto = SensorDTO.model_validate({"sensor_uid": "u", "sensor_code": "GAS-F1", "sensor_model": "BME688",
                                    "measurement_type": "air_quality", "sample_count": 1,
                                    "data": {"temperature_c__avg": 21.5, "iaq_index": 300}})
    assert parse_sensor_values(dto.data) == [MetricValue("temperature_c", "avg", 21.5),
                                             MetricValue("iaq_index", "raw", 300.0)]


def test_power_source_is_stored_like_battery_low():
    """Business rule (14-Nov-2026): power_source is stored as 0/1, 1 = running on battery."""
    assert parse_sensor_values({"power_source": "battery"}) == [MetricValue("power_source", "raw", 1.0)]
    assert parse_sensor_values({"power_source": "main"}) == [MetricValue("power_source", "raw", 0.0)]
    assert parse_sensor_values({"power_source": "solar"}) == []  # unknown text: not guessed
