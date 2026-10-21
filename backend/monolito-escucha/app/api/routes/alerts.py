"""Alert routes - Create, Read, Update."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_alert_service
from app.schemas.alert import AlertCreate, AlertRead, AlertUpdate
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertRead, status_code=201)
async def create_alert(
    alert_in: AlertCreate,
    service: AlertService = Depends(get_alert_service),
):
    return await service.create(alert_in)


@router.get("", response_model=Sequence[AlertRead])
async def list_alerts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: AlertService = Depends(get_alert_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: int,
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/event-uuid/{event_uuid}", response_model=AlertRead | None)
async def get_alert_by_event_uuid(
    event_uuid: str,
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.get_by_event_uuid(event_uuid)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: int,
    alert_in: AlertUpdate,
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.update(alert_id, alert_in)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/reading/{reading_id}", response_model=Sequence[AlertRead])
async def get_alerts_by_reading(
    reading_id: int,
    service: AlertService = Depends(get_alert_service),
):
    return await service.get_by_reading(reading_id)


@router.get("/handled-by/{user_id}", response_model=Sequence[AlertRead])
async def get_alerts_by_handled_user(
    user_id: int,
    service: AlertService = Depends(get_alert_service),
):
    return await service.get_by_handled_user(user_id)


@router.get("/unhandled", response_model=Sequence[AlertRead])
async def get_unhandled_alerts(
    service: AlertService = Depends(get_alert_service),
):
    return await service.get_unhandled()
