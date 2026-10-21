"""SensorType routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_sensor_type_service
from app.schemas.sensor_type import SensorTypeCreate, SensorTypeRead, SensorTypeUpdate
from app.services.sensor_type_service import SensorTypeService

router = APIRouter(prefix="/sensor-types", tags=["sensor-types"])


@router.post("", response_model=SensorTypeRead, status_code=201)
async def create_sensor_type(
    sensor_type_in: SensorTypeCreate,
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    return await service.create(sensor_type_in)


@router.get("", response_model=Sequence[SensorTypeRead])
async def list_sensor_types(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{sensor_type_id}", response_model=SensorTypeRead)
async def get_sensor_type(
    sensor_type_id: int,
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    sensor_type = await service.get(sensor_type_id)
    if not sensor_type:
        raise HTTPException(status_code=404, detail="SensorType not found")
    return sensor_type


@router.patch("/{sensor_type_id}", response_model=SensorTypeRead)
async def update_sensor_type(
    sensor_type_id: int,
    sensor_type_in: SensorTypeUpdate,
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    sensor_type = await service.update(sensor_type_id, sensor_type_in)
    if not sensor_type:
        raise HTTPException(status_code=404, detail="SensorType not found")
    return sensor_type


@router.delete("/{sensor_type_id}", status_code=204)
async def delete_sensor_type(
    sensor_type_id: int,
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    deleted = await service.delete(sensor_type_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="SensorType not found")


@router.get("/{sensor_type_id}/sensors", response_model=Sequence[SensorTypeRead])
async def get_sensor_type_sensors(
    sensor_type_id: int,
    service: SensorTypeService = Depends(get_sensor_type_service),
):
    return await service.get_sensors(sensor_type_id)
