"""Credenciales y TLS del consumidor MQTT: el broker solo acepta conexiones cifradas y autenticadas."""
import ssl
from unittest.mock import MagicMock

from app.services.mqtt_consumer_service import MQTTConsumerService


def make_service(**kwargs) -> MQTTConsumerService:
    return MQTTConsumerService(broker_host="mosquitto", broker_port=8883, **kwargs)


def test_sets_credentials_when_both_are_configured():
    client = MagicMock()

    make_service(username="escucha-consumer", password="secret")._configure_security(client)

    client.username_pw_set.assert_called_once_with("escucha-consumer", "secret")


def test_does_not_set_credentials_when_missing():
    client = MagicMock()

    make_service(username="escucha-consumer")._configure_security(client)

    client.username_pw_set.assert_not_called()


def test_tls_validates_the_broker_certificate_against_the_given_ca():
    client = MagicMock()

    make_service(use_tls=True, ca_file="/certs/ca.crt")._configure_security(client)

    client.tls_set.assert_called_once_with(ca_certs="/certs/ca.crt", cert_reqs=ssl.CERT_REQUIRED)


def test_plain_connection_does_not_enable_tls():
    client = MagicMock()

    make_service()._configure_security(client)

    client.tls_set.assert_not_called()
