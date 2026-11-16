"""Crea (o actualiza) en el broker la cuenta del consumidor de telemetría (monolito-escucha).

El consumidor solo puede suscribirse a `sentinel/v1/+/+/telemetry/aggregate`. Es idempotente:
si la cuenta ya existe, reemplaza su contraseña.

Uso (desde backend/monolito-consulta, con MQTT_HOST/PORT/TLS/CA_FILE, MQTT_ADMIN_* y la cuenta a crear):
    MQTT_CONSUMER_USERNAME=escucha-consumer MQTT_CONSUMER_PASSWORD=... python -m app.scripts.provision_consumer
"""
import os
import sys

from app.api.deps import get_broker_admin
from app.core.broker_admin import BrokerAdminError

DEFAULT_USERNAME = "escucha-consumer"


def main() -> int:
    username = os.getenv("MQTT_CONSUMER_USERNAME") or DEFAULT_USERNAME
    password = os.getenv("MQTT_CONSUMER_PASSWORD")
    if not password:
        print("Falta MQTT_CONSUMER_PASSWORD", file=sys.stderr)
        return 2
    broker = get_broker_admin()
    if broker is None:
        print("Falta MQTT_ADMIN_USERNAME / MQTT_ADMIN_PASSWORD", file=sys.stderr)
        return 2
    try:
        broker.upsert_consumer(username, password)
    except BrokerAdminError as exc:
        print(f"{username}: {exc}", file=sys.stderr)
        return 1
    print(f"{username}: cuenta del consumidor registrada en el broker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
