"""Comandos de administración del broker (dynamic-security) para clientes de nodo."""
import ssl
from unittest.mock import MagicMock

import pytest

from app.core.broker_admin import (
    BrokerAdmin,
    BrokerAdminError,
    build_consumer_commands,
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


def test_consumer_commands_grant_only_the_telemetry_subscription():
    role, client = build_consumer_commands("escucha-consumer", "pw")

    assert role["command"] == "createRole"
    assert role["rolename"] == "consumer-escucha-consumer"
    assert role["acls"] == [{
        "acltype": "subscribePattern",
        "topic": "sentinel/v1/+/+/telemetry/aggregate",
        "priority": 1,
        "allow": True,
    }]
    assert client["command"] == "createClient"
    assert client["username"] == "escucha-consumer"
    assert client["password"] == "pw"
    assert client["roles"] == [{"rolename": "consumer-escucha-consumer"}]


def test_consumer_role_cannot_publish():
    role, _ = build_consumer_commands("escucha-consumer", "pw")

    assert all(acl["acltype"] != "publishClientSend" for acl in role["acls"])


def test_broker_admin_defaults_to_plain_connection():
    admin = BrokerAdmin("mosquitto", 1883, "admin", "pw", "SB-001")

    assert admin.use_tls is False and admin.ca_file is None


def _send_with_fake_client(admin, monkeypatch):
    """Ejecuta una orden con un cliente MQTT falso que nunca responde: el timeout corta la espera."""
    fake = MagicMock()
    monkeypatch.setattr("app.core.broker_admin.mqtt.Client", MagicMock(return_value=fake))
    with pytest.raises(BrokerAdminError):
        admin.disable_node("NODE-FLOOR-1")
    return fake


def test_broker_admin_validates_the_broker_certificate_when_tls_is_enabled(monkeypatch):
    admin = BrokerAdmin("mosquitto", 8883, "admin", "pw", "SB-001", timeout=0.05,
                        use_tls=True, ca_file="/certs/ca.crt")

    fake = _send_with_fake_client(admin, monkeypatch)

    fake.tls_set.assert_called_once_with(ca_certs="/certs/ca.crt", cert_reqs=ssl.CERT_REQUIRED)
    fake.username_pw_set.assert_called_once_with("admin", "pw")


def test_broker_admin_does_not_enable_tls_by_default(monkeypatch):
    admin = BrokerAdmin("mosquitto", 1883, "admin", "pw", "SB-001", timeout=0.05)

    fake = _send_with_fake_client(admin, monkeypatch)

    fake.tls_set.assert_not_called()
