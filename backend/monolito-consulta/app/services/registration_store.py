"""Solicitudes de registro de nodo, en memoria y con tiempo de vida.

Viven solo en memoria: al reiniciar consulta se pierden, y el bridge vuelve a solicitar el registro.
Con varios procesos cada uno tendría su propia lista; por eso consulta corre con un solo worker.
"""
import asyncio
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Callable


class RegistrationStatus(StrEnum):
    PENDING = "pending"      # Esperando que el administrador la revise.
    APPROVED = "approved"    # Aprobada: el nodo ya existe; el token se genera al entregarlo.
    REJECTED = "rejected"
    DELIVERED = "delivered"  # El token ya se entregó al bridge; no se vuelve a entregar.
    EXPIRED = "expired"


@dataclass
class Registration:
    id: str
    code: str
    name: str
    building_code: str
    zone_code: str
    poll_secret_hash: str
    created_at: datetime
    expires_at: datetime
    status: RegistrationStatus = RegistrationStatus.PENDING
    zone_id: int | None = None
    node_id: int | None = None


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class RegistrationStore:
    """Almacén en memoria. No es seguro para hilos por sí solo: el servicio lo serializa."""

    def __init__(self, ttl_seconds: int, clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock
        self._items: dict[str, Registration] = {}
        # Serializa aprobar, rechazar y entregar: cada solicitud cambia de estado una sola vez.
        self.lock = asyncio.Lock()

    def now(self) -> datetime:
        return self._clock()

    def _expire(self) -> None:
        now = self.now()
        for item in self._items.values():
            if item.status in (RegistrationStatus.PENDING, RegistrationStatus.APPROVED) and now >= item.expires_at:
                item.status = RegistrationStatus.EXPIRED

    def create(self, code: str, name: str, building_code: str, zone_code: str) -> tuple[Registration, str]:
        """Crea la solicitud. Devuelve la solicitud y el secreto de sondeo, que solo se muestra una vez."""
        self._expire()
        secret = secrets.token_urlsafe(32)
        now = self.now()
        item = Registration(
            id=uuid.uuid4().hex, code=code, name=name, building_code=building_code, zone_code=zone_code,
            poll_secret_hash=hash_secret(secret), created_at=now, expires_at=now + self.ttl,
        )
        self._items[item.id] = item
        return item, secret

    def get(self, registration_id: str) -> Registration | None:
        self._expire()
        return self._items.get(registration_id)

    def pending(self) -> list[Registration]:
        self._expire()
        return sorted(
            (i for i in self._items.values() if i.status == RegistrationStatus.PENDING),
            key=lambda i: i.created_at,
        )

    def has_open_request_for(self, code: str) -> bool:
        self._expire()
        return any(
            i.code == code and i.status in (RegistrationStatus.PENDING, RegistrationStatus.APPROVED)
            for i in self._items.values()
        )

    @staticmethod
    def verify_secret(item: Registration, secret: str) -> bool:
        return hmac.compare_digest(item.poll_secret_hash, hash_secret(secret))

    def renew(self, item: Registration) -> None:
        """Al aprobar, el bridge dispone de otro tiempo completo para recoger el token."""
        item.expires_at = self.now() + self.ttl
