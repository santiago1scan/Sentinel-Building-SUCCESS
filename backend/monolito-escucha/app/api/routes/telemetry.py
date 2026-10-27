"""Telemetry routes - Process incoming telemetry data from bridge."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_telemetry_service
from app.services.telemetry_service import TelemetryService
from app.services.DTOS.telemetry_dto import TelemetryAggregateDTO

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/aggregate", status_code=202)
async def process_telemetry_aggregate(
    telemetry_in: TelemetryAggregateDTO,
    service: TelemetryService = Depends(get_telemetry_service),
):
    """
    Process telemetry aggregate from bridge and save readings to database.

    - **Request body**: TelemetryAggregateDTO with building, bridges, sensors, and data
    - **Returns**: Message UID, count of created readings, and any errors
    """
    try:
        result = await service.process_telemetry(telemetry_in)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/node/{node_id}", response_model=dict)
async def get_telemetry_by_node(
    node_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: TelemetryService = Depends(get_telemetry_service),
):
    """
    Get complete telemetry information for a specific node (paginated).

    Includes:
    - Node details (code, name, IP, storage, signals)
    - Zone and building information
    - All readings received by this node with complete sensor data
    - Sensor types and characteristics

    - **node_id**: Node ID to filter readings
    - **limit**: Number of records per page (1-1000, default: 100)
    - **offset**: Pagination offset (default: 0)

    **Returns**: Complete telemetry data with pagination
    """
    try:
        result = await service.get_telemetry_by_node(node_id, limit, offset)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
