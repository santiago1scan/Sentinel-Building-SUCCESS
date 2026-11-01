"""ConnectivityLog routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_connectivity_log_service
from app.schemas.connectivity_log import (
    ConnectivityLogCreate,
    ConnectivityLogRead,
    ConnectivityLogUpdate,
)
from app.services.connectivity_log_service import ConnectivityLogService

router = APIRouter(prefix="/connectivity-logs", tags=["connectivity-logs"])


@router.post("", response_model=ConnectivityLogRead, status_code=201)
async def create_connectivity_log(
    log_in: ConnectivityLogCreate,
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    return await service.create(log_in)


@router.get("", response_model=Sequence[ConnectivityLogRead])
async def list_connectivity_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{connectivity_id}", response_model=ConnectivityLogRead)
async def get_connectivity_log(
    connectivity_id: int,
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    log = await service.get(connectivity_id)
    if not log:
        raise HTTPException(status_code=404, detail="ConnectivityLog not found")
    return log


@router.patch("/{connectivity_id}", response_model=ConnectivityLogRead)
async def update_connectivity_log(
    connectivity_id: int,
    log_in: ConnectivityLogUpdate,
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    log = await service.update(connectivity_id, log_in)
    if not log:
        raise HTTPException(status_code=404, detail="ConnectivityLog not found")
    return log


@router.get("/node/{node_id}", response_model=Sequence[ConnectivityLogRead])
async def get_connectivity_logs_by_node(
    node_id: int,
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    return await service.get_by_node(node_id)


@router.get("/node/{node_id}/active", response_model=Sequence[ConnectivityLogRead])
async def get_active_connectivity_logs_by_node(
    node_id: int,
    service: ConnectivityLogService = Depends(get_connectivity_log_service),
):
    return await service.get_active_by_node(node_id)
