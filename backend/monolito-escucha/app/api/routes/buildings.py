"""Building routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_building_service
from app.schemas.building import BuildingCreate, BuildingRead, BuildingUpdate
from app.services.building_service import BuildingService

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.post("", response_model=BuildingRead, status_code=201)
async def create_building(
    building_in: BuildingCreate,
    service: BuildingService = Depends(get_building_service),
):
    return await service.create(building_in)


@router.get("", response_model=Sequence[BuildingRead])
async def list_buildings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: BuildingService = Depends(get_building_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{building_id}", response_model=BuildingRead)
async def get_building(
    building_id: int,
    service: BuildingService = Depends(get_building_service),
):
    return await service.get(building_id)


@router.patch("/{building_id}", response_model=BuildingRead)
async def update_building(
    building_id: int,
    building_in: BuildingUpdate,
    service: BuildingService = Depends(get_building_service),
):
    return await service.update(building_id, building_in)


@router.delete("/{building_id}", status_code=204)
async def delete_building(
    building_id: int,
    service: BuildingService = Depends(get_building_service),
):
    await service.delete(building_id)


@router.get("/{building_id}/zones", response_model=Sequence[BuildingRead])
async def get_building_zones(
    building_id: int,
    service: BuildingService = Depends(get_building_service),
):
    return await service.get_zones(building_id)
