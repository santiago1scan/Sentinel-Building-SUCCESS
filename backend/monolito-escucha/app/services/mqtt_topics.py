"""Topics propios de cada nodo: sentinel/v1/{building_code}/{node_code}/telemetry/aggregate.

Funciones puras, sin MQTT ni base de datos, para poder probarlas aisladas.
"""
from collections.abc import Iterable

TOPIC_ROOT = "sentinel/v1"
AGGREGATE_SUFFIX = ("telemetry", "aggregate")

# Suscripción del consumidor: un solo comodín por edificio y por nodo.
AGGREGATE_SUBSCRIPTION = f"{TOPIC_ROOT}/+/+/telemetry/aggregate"


def parse_aggregate_topic(topic: str) -> tuple[str, str] | None:
    """Return (building_code, node_code) for a node aggregate topic, or None if it does not match."""
    parts = topic.split("/")
    if len(parts) != 6:
        return None
    root_a, root_b, building_code, node_code, *suffix = parts
    if f"{root_a}/{root_b}" != TOPIC_ROOT or tuple(suffix) != AGGREGATE_SUFFIX:
        return None
    if not building_code or not node_code:
        return None
    return building_code, node_code


def bridges_belong_to_node(bridge_codes: Iterable[str], node_code: str) -> bool:
    """True when every bridge reported in the payload is the node that published the topic."""
    return all(code == node_code for code in bridge_codes)
