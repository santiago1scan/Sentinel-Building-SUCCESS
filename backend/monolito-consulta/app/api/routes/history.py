"""Route: half-hour history of a sensor variable."""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.history import HistoryRow
from app.services.history_service import HistoryService, MetricNotFound

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryRow])
async def half_hour_history(
    sensor_id: int,
    metric_code: str = Query(..., description="Variable, e.g. temperature_c"),
    start: datetime.datetime = Query(..., alias="from", description="With time zone"),
    end: datetime.datetime = Query(..., alias="to", description="With time zone"),
    db: AsyncSession = Depends(get_db),
):
    """Avg, max and min of every half hour between from and to. Half hours without a summary: no_data = true."""
    try:
        return await HistoryService(db).half_hours(sensor_id, metric_code, start, end)
    except MetricNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
