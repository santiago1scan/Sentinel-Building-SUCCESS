"""Comandos de administración del broker (dynamic-security) para clientes de nodo."""
from app.core.broker_admin import (
    build_create_node_commands,
    build_disable_node_commands,
    find_command_errors,
    node_publish_topic,
    node_role_name,
)


def test_create_node_commands_grant_only_the_node_topic():
    commands = build_create_node_commands("SB-001", "NODE-FLOOR-1", "tok-1")

    role, client = commands
    assert role["command"] == "createRole"
    assert role["rolename"] == "node-NODE-FLOOR-1"
    assert role["acls"] == [{
        "acltype": "publishClientSend",
        "topic": "sentinel/v1/SB-001/NODE-FLOOR-1/telemetry/aggregate",
        "priority": 1,
        "allow": True,
    }]
    assert client["command"] == "createClient"
    assert client["username"] == "NODE-FLOOR-1"
    assert client["password"] == "tok-1"
    assert client["roles"] == [{"rolename": "node-NODE-FLOOR-1"}]


def test_topic_is_literal_per_node_not_a_wildcard():
    # %u y + no entregan mensajes en dynamic-security 2.0.22: el topic debe ser literal.
    topic = node_publish_topic("SB-001", "NODE-FLOOR-2")

    assert "+" not in topic and "#" not in topic and "%u" not in topic
    assert topic == "sentinel/v1/SB-001/NODE-FLOOR-2/telemetry/aggregate"


def test_disable_command_targets_the_node_client():
    assert build_disable_node_commands("NODE-FLOOR-1") == [
        {"command": "disableClient", "username": "NODE-FLOOR-1"}
    ]


def test_role_name_is_derived_from_node_code():
    assert node_role_name("NODE-FLOOR-1") == "node-NODE-FLOOR-1"


def test_no_errors_when_every_command_succeeds():
    response = {"responses": [{"command": "createRole"}, {"command": "createClient"}]}

    assert find_command_errors(response) == []


def test_reports_each_failed_command():
    response = {"responses": [
        {"command": "createRole", "error": "Role already exists"},
        {"command": "createClient", "error": "Client already exists"},
    ]}

    assert find_command_errors(response) == [
        "createRole: Role already exists",
        "createClient: Client already exists",
    ]
