"""Fakes and builders shared by the node authentication tests. No database involved."""
from datetime import datetime, timezone

from app.core.security import hash_token
from app.models.node import Node


class FakeNodeRepository:
    """Stands in for NodeRepository: looks nodes up by the token hash they were stored with."""

    def __init__(self, nodes_by_token: dict[str, Node] | None = None):
        self._nodes_by_hash: dict[str, Node] = {}
        for token, node in (nodes_by_token or {}).items():
            self._nodes_by_hash[hash_token(token)] = node
        self.requested_hashes: list[str] = []

    async def get_by_token_hash(self, token_hash: str) -> Node | None:
        self.requested_hashes.append(token_hash)
        return self._nodes_by_hash.get(token_hash)


class FakeTelemetryService:
    """Stands in for TelemetryService and records whether the route reached it."""

    def __init__(self):
        self.calls = []

    async def process_telemetry(self, telemetry):
        self.calls.append(telemetry)
        return {"message_uid": telemetry.message_uid, "readings_created": 0, "errors": []}


def make_node(code: str = "NODE-FLOOR-1", node_id: int = 1) -> Node:
    return Node(node_id=node_id, code=code, name=f"Bridge {code}", zone_id=1)


def make_telemetry_payload(bridge_codes: list[str]) -> dict:
    """Minimal body accepted by TelemetryAggregateDTO, with one bridge per code."""
    now = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc).isoformat()
    return {
        "schema_version": "1.0",
        "message_uid": "msg-0001",
        "message_type": "telemetry_aggregate",
        "building_uid": "bld-1",
        "building_code": "SB-001",
        "generated_at": now,
        "sent_at": now,
        "sequence_number": 1,
        "priority": "normal",
        "quality": "valid",
        "delivery_policy": "best_effort",
        "delivery_status": "sent",
        "transport": "rest",
        "window": {
            "start": now,
            "end": now,
            "duration_seconds": 60.0,
            "sample_count": 0,
        },
        "bridges": [
            {
                "node_uid": f"uid-{code}",
                "node_code": code,
                "node_name": f"Bridge {code}",
                "floor": 1,
                "zone_uid": "zone-1",
                "zone_code": "Z-1",
                "sensors": [],
            }
            for code in bridge_codes
        ],
    }
