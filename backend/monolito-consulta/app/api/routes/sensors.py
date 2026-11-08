"""Sensor routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_sensor_service
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("", response_model=SensorRead, status_code=201)
async def create_sensor(
    sensor_in: SensorCreate,
    service: SensorService = Depends(get_sensor_service),
):
    return await service.create(sensor_in)


@router.get("", response_model=Sequence[SensorRead])
async def list_sensors(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{sensor_id}", response_model=SensorRead)
async def get_sensor(
    sensor_id: int,
    service: SensorService = Depends(get_sensor_service),
):
    sensor = await service.get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.get("/code/{code}", response_model=SensorRead | None)
async def get_sensor_by_code(
    code: str,
    service: SensorService = Depends(get_sensor_service),
):
    sensor = await service.get_by_code(code)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.patch("/{sensor_id}", response_model=SensorRead)
async def update_sensor(
    sensor_id: int,
    sensor_in: SensorUpdate,
    service: SensorService = Depends(get_sensor_service),
):
    sensor = await service.update(sensor_id, sensor_in)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.delete("/{sensor_id}", status_code=204)
async def delete_sensor(
    sensor_id: int,
    service: SensorService = Depends(get_sensor_service),
):
    deleted = await service.delete(sensor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sensor not found")


@router.get("/primary-node/{primary_node_id}", response_model=Sequence[SensorRead])
async def get_sensors_by_primary_node(
    primary_node_id: int,
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_by_primary_node(primary_node_id)


@router.get("/sensor-type/{sensor_type_id}", response_model=Sequence[SensorRead])
async def get_sensors_by_sensor_type(
    sensor_type_id: int,
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_by_sensor_type(sensor_type_id)


@router.get("/{sensor_id}/readings", response_model=Sequence[SensorRead])
async def get_sensor_readings(
    sensor_id: int,
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_readings(sensor_id)
