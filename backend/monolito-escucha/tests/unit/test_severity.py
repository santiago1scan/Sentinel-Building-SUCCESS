"""Severity rule (24-Nov-2026), applied to the open out-of-range alerts of one node.

Emergency: any motion or energy alert, or temperature and air quality at the same time.
Minor: anything else (only heat, e.g. a candle; only air quality, e.g. perfume).
"""
from app.analytics.severity import EMERGENCIA, LEVE, classify_node


def test_only_temperature_is_minor():
    assert classify_node(["maximum_c", "hot_pixels"]) == LEVE


def test_only_air_quality_is_minor():
    assert classify_node(["iaq_index", "tvoc_ppb"]) == LEVE


def test_temperature_and_air_quality_together_is_emergency():
    assert classify_node(["maximum_c", "tvoc_ppb"]) == EMERGENCIA


def test_motion_is_emergency():
    assert classify_node(["rms_g"]) == EMERGENCIA


def test_energy_is_emergency():
    assert classify_node(["bus_voltage_v"]) == EMERGENCIA


def test_nothing_open_has_no_severity():
    assert classify_node([]) is None


def test_unknown_metric_is_ignored():
    # A variable created on first sight with no category must not break the rule nor raise it.
    assert classify_node(["rare_metric"]) is None
    assert classify_node(["rare_metric", "iaq_index"]) == LEVE
