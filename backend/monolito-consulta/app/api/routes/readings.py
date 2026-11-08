"""Reading routes - Create and Read only."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_reading_service
from app.schemas.reading import ReadingCreate, ReadingRead
from app.services.reading_service import ReadingService

router = APIRouter(prefix="/readings", tags=["readings"])


@router.post("", response_model=ReadingRead, status_code=201)
async def create_reading(
    reading_in: ReadingCreate,
    service: ReadingService = Depends(get_reading_service),
):
    return await service.create(reading_in)


@router.get("", response_model=Sequence[ReadingRead])
async def list_readings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ReadingService = Depends(get_reading_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{reading_id}", response_model=ReadingRead)
async def get_reading(
    reading_id: int,
    service: ReadingService = Depends(get_reading_service),
):
    reading = await service.get(reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading


@router.get("/sensor/{sensor_id}", response_model=Sequence[ReadingRead])
async def get_readings_by_sensor(
    sensor_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ReadingService = Depends(get_reading_service),
):
    return await service.get_by_sensor(sensor_id, limit, offset)


@router.get("/receiving-node/{receiving_node_id}", response_model=Sequence[ReadingRead])
async def get_readings_by_receiving_node(
    receiving_node_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ReadingService = Depends(get_reading_service),
):
    return await service.get_by_receiving_node(receiving_node_id, limit, offset)


@router.get("/sequence/{sequence_number}", response_model=Sequence[ReadingRead])
async def get_readings_by_sequence_number(
    sequence_number: int,
    service: ReadingService = Depends(get_reading_service),
):
    return await service.get_by_sequence_number(sequence_number)


@router.get("/{reading_id}/alerts", response_model=Sequence[ReadingRead])
async def get_reading_alerts(
    reading_id: int,
    service: ReadingService = Depends(get_reading_service),
):
    return await service.get_alerts(reading_id)
