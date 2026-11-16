"""Floor routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_floor_service
from app.schemas.floor import FloorCreate, FloorRead, FloorUpdate
from app.services.floor_service import FloorService

router = APIRouter(prefix="/floors", tags=["floors"])


@router.post("", response_model=FloorRead, status_code=201)
async def create_floor(
    floor_in: FloorCreate,
    service: FloorService = Depends(get_floor_service),
):
    return await service.create(floor_in)


@router.get("", response_model=Sequence[FloorRead])
async def list_floors(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: FloorService = Depends(get_floor_service),
):
    return await service.get_all(limit=limit, offset=offset)


# Fixed paths go before "/{floor_id}"; declared after it they never match (the id would fail as an integer).
@router.get("/building/{building_id}", response_model=Sequence[FloorRead])
async def get_floors_by_building(
    building_id: int,
    service: FloorService = Depends(get_floor_service),
):
    return await service.get_by_building(building_id)


@router.get("/{floor_id}", response_model=FloorRead)
async def get_floor(
    floor_id: int,
    service: FloorService = Depends(get_floor_service),
):
    return await service.get(floor_id)


@router.patch("/{floor_id}", response_model=FloorRead)
async def update_floor(
    floor_id: int,
    floor_in: FloorUpdate,
    service: FloorService = Depends(get_floor_service),
):
    return await service.update(floor_id, floor_in)


@router.delete("/{floor_id}", status_code=204)
async def delete_floor(
    floor_id: int,
    service: FloorService = Depends(get_floor_service),
):
    await service.delete(floor_id)
