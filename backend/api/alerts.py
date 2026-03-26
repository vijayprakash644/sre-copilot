"""
Alert history API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query

from db import get_alerts, get_alert_by_id, get_alert_stats
from models import AlertWithTriage, AlertStats

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertWithTriage])
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AlertWithTriage]:
    return await get_alerts(limit=limit, offset=offset)


@router.get("/stats", response_model=AlertStats)
async def alert_stats() -> AlertStats:
    data = await get_alert_stats()
    return AlertStats(**data)


@router.get("/{alert_id}", response_model=AlertWithTriage)
async def get_alert(alert_id: str) -> AlertWithTriage:
    result = await get_alert_by_id(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result
