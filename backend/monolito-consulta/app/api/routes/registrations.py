"""Rutas de registro de nodos por solicitud."""
import asyncio
import json
import time
from collections.abc import AsyncIterator, Sequence

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.auth import require_user, require_user_or_query_token
from app.api.deps import get_registration_service, get_registration_store
from app.schemas.registration import (
    ApprovedRegistrationRead,
    ApproveRegistrationRequest,
    DeliveredNodeRead,
    PendingRegistrationRead,
    RegistrationAccepted,
    RegistrationRequest,
)
from app.services.registration_service import RegistrationService
from app.services.registration_store import Registration, RegistrationStore

router = APIRouter(prefix="/registrations", tags=["registrations"])


def _pending_read(item: Registration) -> PendingRegistrationRead:
    return PendingRegistrationRead(
        registration_id=item.id, code=item.code, name=item.name,
        building_code=item.building_code, zone_code=item.zone_code,
        status=item.status.value, created_at=item.created_at, expires_at=item.expires_at,
    )


@router.post("", status_code=202, response_model=RegistrationAccepted)
async def request_registration(
    body: RegistrationRequest,
    service: RegistrationService = Depends(get_registration_service),
):
    """El bridge solicita registrarse. Devuelve el secreto de sondeo, que no se vuelve a mostrar."""
    item, secret = await service.request(body)
    return RegistrationAccepted(registration_id=item.id, poll_secret=secret, expires_at=item.expires_at)


@router.get("/pending", response_model=Sequence[PendingRegistrationRead], dependencies=[Depends(require_user)])
async def list_pending_registrations(
    service: RegistrationService = Depends(get_registration_service),
):
    """Solicitudes que esperan revisión del administrador (la alerta del frontend)."""
    return [_pending_read(item) for item in service.list_pending()]


def format_sse(event: str, data: object) -> str:
    """Un evento del protocolo Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


KEEPALIVE_SECONDS = 15


async def _pending_events(store: RegistrationStore) -> AsyncIterator[str]:
    """Emite la lista de pendientes al conectar y cada vez que cambia; comentarios para mantener viva la conexión."""
    last_version = None
    last_beat = time.monotonic()
    while True:
        if store.version != last_version:
            last_version = store.version
            pending = [_pending_read(item).model_dump(mode="json") for item in store.pending()]
            yield format_sse("pending", pending)
            last_beat = time.monotonic()
        elif time.monotonic() - last_beat >= KEEPALIVE_SECONDS:
            yield ": keepalive\n\n"
            last_beat = time.monotonic()
        await asyncio.sleep(1)


@router.get("/stream", response_class=StreamingResponse, dependencies=[Depends(require_user_or_query_token)])
async def stream_pending_registrations(store: RegistrationStore = Depends(get_registration_store)):
    """Server-Sent Events: el administrador recibe las solicitudes pendientes sin recargar."""
    return StreamingResponse(
        _pending_events(store),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{registration_id}/approve", response_model=ApprovedRegistrationRead, dependencies=[Depends(require_user)])
async def approve_registration(
    registration_id: str,
    body: ApproveRegistrationRequest,
    service: RegistrationService = Depends(get_registration_service),
):
    """Aprueba la solicitud en una zona. Crea el nodo; el token se entrega cuando el bridge lo recoge."""
    item = await service.approve(registration_id, body.zone_id)
    return ApprovedRegistrationRead(
        registration_id=item.id, status=item.status.value, node_id=item.node_id, zone_id=item.zone_id,
    )


@router.post("/{registration_id}/reject", response_model=PendingRegistrationRead, dependencies=[Depends(require_user)])
async def reject_registration(
    registration_id: str,
    service: RegistrationService = Depends(get_registration_service),
):
    return _pending_read(await service.reject(registration_id))


@router.get("/{registration_id}", responses={202: {"description": "Pendiente de aprobación"}})
async def poll_registration(
    registration_id: str,
    x_poll_secret: str = Header(alias="X-Poll-Secret"),
    service: RegistrationService = Depends(get_registration_service),
):
    """El bridge recoge el resultado. 202 mientras espera; 200 con el token una sola vez."""
    delivered = await service.deliver(registration_id, x_poll_secret)
    if delivered is None:
        return JSONResponse(status_code=202, content={"status": "pending"})
    return DeliveredNodeRead(**delivered.model_dump())
