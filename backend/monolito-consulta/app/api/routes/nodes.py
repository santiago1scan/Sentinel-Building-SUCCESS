"""Node routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_node_service
from app.schemas.connectivity_log import ConnectivityLogRead
from app.schemas.node import NodeCreate, NodeCreateResponse, NodeRead, NodeUpdate
from app.schemas.reading import ReadingRead
from app.schemas.sensor import SensorRead
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("", response_model=NodeCreateResponse, status_code=201)
async def create_node(
    node_in: NodeCreate,
    service: NodeService = Depends(get_node_service),
):
    return await service.create(node_in)


@router.post("/{node_id}/revoke", status_code=204)
async def revoke_node(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    """Revoca el nodo: su cliente en el broker queda deshabilitado y su sesión se corta."""
    await service.revoke(node_id)


@router.get("", response_model=Sequence[NodeRead])
async def list_nodes(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: NodeService = Depends(get_node_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{node_id}", response_model=NodeRead)
async def get_node(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    node = await service.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.get("/code/{code}", response_model=NodeRead | None)
async def get_node_by_code(
    code: str,
    service: NodeService = Depends(get_node_service),
):
    node = await service.get_by_code(code)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.patch("/{node_id}", response_model=NodeRead)
async def update_node(
    node_id: int,
    node_in: NodeUpdate,
    service: NodeService = Depends(get_node_service),
):
    node = await service.update(node_id, node_in)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.delete("/{node_id}", status_code=204)
async def delete_node(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    deleted = await service.delete(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")


@router.get("/zone/{zone_id}", response_model=Sequence[NodeRead])
async def get_nodes_by_zone(
    zone_id: int,
    service: NodeService = Depends(get_node_service),
):
    return await service.get_by_zone(zone_id)


@router.get("/{node_id}/sensors", response_model=Sequence[SensorRead])
async def get_node_sensors(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    return await service.get_sensors(node_id)


@router.get("/{node_id}/connectivity-logs", response_model=Sequence[ConnectivityLogRead])
async def get_node_connectivity_logs(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    return await service.get_connectivity_logs(node_id)


@router.get("/{node_id}/received-readings", response_model=Sequence[ReadingRead])
async def get_node_received_readings(
    node_id: int,
    service: NodeService = Depends(get_node_service),
):
    return await service.get_received_readings(node_id)
