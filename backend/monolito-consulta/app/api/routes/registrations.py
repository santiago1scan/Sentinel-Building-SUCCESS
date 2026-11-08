"""Rutas de registro de nodos por solicitud."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.api.deps import get_registration_service
from app.schemas.registration import (
    ApprovedRegistrationRead,
    ApproveRegistrationRequest,
    DeliveredNodeRead,
    PendingRegistrationRead,
    RegistrationAccepted,
    RegistrationRequest,
)
from app.services.registration_service import RegistrationService
from app.services.registration_store import Registration

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


@router.get("/pending", response_model=Sequence[PendingRegistrationRead])
async def list_pending_registrations(
    service: RegistrationService = Depends(get_registration_service),
):
    """Solicitudes que esperan revisión del administrador (la alerta del frontend)."""
    return [_pending_read(item) for item in service.list_pending()]


@router.post("/{registration_id}/approve", response_model=ApprovedRegistrationRead)
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


@router.post("/{registration_id}/reject", response_model=PendingRegistrationRead)
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
