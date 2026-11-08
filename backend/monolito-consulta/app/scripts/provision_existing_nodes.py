"""Da de alta en el broker los clientes de nodos que ya existían antes del plugin dynamic-security.

Lee los tokens de SENTINEL_NODE_TOKENS ("NODE-FLOOR-1=token,NODE-FLOOR-2=token"), comprueba que
cada token corresponda al hash guardado en la BD y crea su cliente en el broker.

Uso (desde backend/monolito-consulta, con DATABASE_URL, MQTT_ADMIN_* y SENTINEL_NODE_TOKENS):
    python -m app.scripts.provision_existing_nodes
"""
import asyncio
import os
import sys

from sqlalchemy import select

from app.api.deps import get_broker_admin
from app.core.broker_admin import BrokerAdminError
from app.core.database import get_db_context
from app.core.security import hash_token
from app.models.node import Node


def parse_tokens(spec: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for item in spec.split(","):
        node, sep, token = item.strip().partition("=")
        if sep and node.strip() and token.strip():
            tokens[node.strip()] = token.strip()
    return tokens


async def provision(tokens: dict[str, str]) -> int:
    broker = get_broker_admin()
    if broker is None:
        print("Falta MQTT_ADMIN_USERNAME / MQTT_ADMIN_PASSWORD", file=sys.stderr)
        return 2
    failures = 0
    async with get_db_context() as session:
        for code, token in sorted(tokens.items()):
            node = (await session.execute(select(Node).where(Node.code == code))).scalar_one_or_none()
            if node is None:
                print(f"{code}: no existe en la BD")
                failures += 1
                continue
            if node.token_hash != hash_token(token):
                print(f"{code}: el token no corresponde al hash guardado en la BD")
                failures += 1
                continue
            try:
                await asyncio.to_thread(broker.create_node, code, token)
                print(f"{code}: cliente creado en el broker")
            except BrokerAdminError as exc:
                print(f"{code}: {exc}")
                failures += 1
    return 1 if failures else 0


def main() -> None:
    tokens = parse_tokens(os.getenv("SENTINEL_NODE_TOKENS", ""))
    if not tokens:
        print("SENTINEL_NODE_TOKENS está vacío", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(provision(tokens)))


if __name__ == "__main__":
    main()
