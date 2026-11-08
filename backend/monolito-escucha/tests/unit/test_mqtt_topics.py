"""Unit tests for node-owned MQTT topics."""
import pytest

from app.services.mqtt_topics import (
    AGGREGATE_SUBSCRIPTION,
    bridges_belong_to_node,
    parse_aggregate_topic,
)


def test_parses_building_and_node_from_aggregate_topic():
    assert parse_aggregate_topic("sentinel/v1/SB-001/NODE-FLOOR-1/telemetry/aggregate") == (
        "SB-001",
        "NODE-FLOOR-1",
    )


@pytest.mark.parametrize(
    "topic",
    [
        "sentinel/v1/SB-001/telemetry/aggregate",  # topic antiguo a nivel de edificio
        "sentinel/v1/SB-001/NODE-FLOOR-1/telemetry/batch",  # otro tipo de mensaje
        "sentinel/v1/SB-001/NODE-FLOOR-1/extra/telemetry/aggregate",  # segmento de más
        "sentinel/v2/SB-001/NODE-FLOOR-1/telemetry/aggregate",  # versión distinta
        "other/v1/SB-001/NODE-FLOOR-1/telemetry/aggregate",  # raíz distinta
        "sentinel/v1//NODE-FLOOR-1/telemetry/aggregate",  # edificio vacío
        "sentinel/v1/SB-001//telemetry/aggregate",  # nodo vacío
        "",
    ],
)
def test_rejects_topics_that_are_not_node_aggregate(topic):
    assert parse_aggregate_topic(topic) is None


def test_subscription_matches_one_level_for_building_and_node():
    assert AGGREGATE_SUBSCRIPTION == "sentinel/v1/+/+/telemetry/aggregate"


def test_bridges_belong_to_node_when_all_codes_match():
    assert bridges_belong_to_node(["NODE-FLOOR-1", "NODE-FLOOR-1"], "NODE-FLOOR-1")


def test_bridges_do_not_belong_when_one_code_differs():
    assert not bridges_belong_to_node(["NODE-FLOOR-1", "NODE-FLOOR-2"], "NODE-FLOOR-1")


def test_empty_bridge_list_is_accepted():
    assert bridges_belong_to_node([], "NODE-FLOOR-1")
