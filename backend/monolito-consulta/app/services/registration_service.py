"""Registro de nodos por solicitud: el bridge pide, el administrador aprueba, el bridge recoge el token.

Reglas:
- El nodo no existe hasta que el administrador lo aprueba.
- El token se genera al entregarlo, no al aprobar: nunca queda una credencial en espera.
- El token se entrega una sola vez, y solo con el secreto de sondeo que recibió el bridge.
"""
import asyncio

from app.core.broker_admin import BrokerAdmin, BrokerAdminError
from app.core.exceptions import ConflictError, GoneError, NotFoundError, ServiceUnavailableError
from app.core.security import generate_node_token, hash_token
from app.repositories.node_repository import NodeRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.registration import DeliveredNodeRead, RegistrationRequest
from app.services.registration_store import Registration, RegistrationStatus, RegistrationStore


class RegistrationService:
    def __init__(
        self,
        store: RegistrationStore,
        nodes: NodeRepository,
        zones: ZoneRepository,
        broker: BrokerAdmin | None,
    ) -> None:
        self.store = store
        self.nodes = nodes
        self.zones = zones
        self.broker = broker

    def _require(self, registration_id: str) -> Registration:
        item = self.store.get(registration_id)
        if item is None:
            raise NotFoundError("Solicitud de registro no encontrada")
        return item

    async def request(self, body: RegistrationRequest) -> tuple[Registration, str]:
        if await self.nodes.get_by_code(body.code) is not None:
            raise ConflictError(f"Ya existe un nodo con código {body.code}")
        if self.store.has_open_request_for(body.code):
            raise ConflictError(f"Ya hay una solicitud abierta para {body.code}")
        return self.store.create(body.code, body.name, body.building_code, body.zone_code)

    def list_pending(self) -> list[Registration]:
        return self.store.pending()

    async def approve(self, registration_id: str, zone_id: int) -> Registration:
        async with self.store.lock:
            item = self._require(registration_id)
            if item.status != RegistrationStatus.PENDING:
                raise ConflictError(f"La solicitud está {item.status.value}")
            if await self.zones.get(zone_id) is None:
                raise NotFoundError(f"La zona {zone_id} no existe")
            if await self.nodes.get_by_code(item.code) is not None:
                raise ConflictError(f"Ya existe un nodo con código {item.code}")
            node = await self.nodes.create({
                "code": item.code, "name": item.name, "zone_id": zone_id, "token_hash": None,
            })
            item.status = RegistrationStatus.APPROVED
            item.zone_id = zone_id
            item.node_id = node.node_id
            self.store.renew(item)
            return item

    async def reject(self, registration_id: str) -> Registration:
        async with self.store.lock:
            item = self._require(registration_id)
            if item.status != RegistrationStatus.PENDING:
                raise ConflictError(f"La solicitud está {item.status.value}")
            item.status = RegistrationStatus.REJECTED
            return item

    async def deliver(self, registration_id: str, poll_secret: str) -> DeliveredNodeRead | None:
        """Devuelve None mientras la solicitud está pendiente; el token solo en la primera entrega."""
        async with self.store.lock:
            item = self._require(registration_id)
            if not self.store.verify_secret(item, poll_secret):
                # Mismo mensaje que una solicitud inexistente: no revela que el id existe.
                raise NotFoundError("Solicitud de registro no encontrada")
            if item.status == RegistrationStatus.PENDING:
                return None
            if item.status != RegistrationStatus.APPROVED:
                raise GoneError(f"La solicitud está {item.status.value}; el token no está disponible")
            if self.broker is None:
                raise ServiceUnavailableError("El broker MQTT no está configurado para registrar nodos")

            token = generate_node_token()
            node = await self.nodes.get(item.node_id)
            node.token_hash = hash_token(token)
            # 1) Confirmar en la BD. 2) Solo entonces tocar el broker: si la BD falla, el broker
            # no queda con un cliente que la BD no conoce.
            await self.nodes.session.commit()
            try:
                await asyncio.to_thread(self.broker.upsert_node, item.code, token)
            except BrokerAdminError as exc:
                # La solicitud sigue aprobada. El reintento genera otro token y reemplaza este.
                raise ServiceUnavailableError(f"No se pudo registrar el nodo en el broker: {exc}") from exc

            item.status = RegistrationStatus.DELIVERED
            return DeliveredNodeRead(node_id=node.node_id, node_code=item.code, token=token)
