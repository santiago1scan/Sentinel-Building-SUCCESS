"""Zone routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_zone_service
from app.schemas.zone import ZoneCreate, ZoneRead, ZoneUpdate
from app.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("", response_model=ZoneRead, status_code=201)
async def create_zone(
    zone_in: ZoneCreate,
    service: ZoneService = Depends(get_zone_service),
):
    return await service.create(zone_in)


@router.get("", response_model=Sequence[ZoneRead])
async def list_zones(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ZoneService = Depends(get_zone_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{zone_id}", response_model=ZoneRead)
async def get_zone(
    zone_id: int,
    service: ZoneService = Depends(get_zone_service),
):
    zone = await service.get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.patch("/{zone_id}", response_model=ZoneRead)
async def update_zone(
    zone_id: int,
    zone_in: ZoneUpdate,
    service: ZoneService = Depends(get_zone_service),
):
    zone = await service.update(zone_id, zone_in)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: int,
    service: ZoneService = Depends(get_zone_service),
):
    deleted = await service.delete(zone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Zone not found")


@router.get("/building/{building_id}", response_model=Sequence[ZoneRead])
async def get_zones_by_building(
    building_id: int,
    service: ZoneService = Depends(get_zone_service),
):
    return await service.get_by_building(building_id)
