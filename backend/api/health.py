"""
Health check endpoints.
/health — liveness probe
/ready  — readiness probe (checks DB + LLM connectivity)
"""
from fastapi import APIRouter

from ai.client import validate_llm_connection
from config import get_settings
from db import check_db_health
from models import HealthStatus, ReadyStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    settings = get_settings()
    return HealthStatus(status="ok", mode=settings.deployment_mode.value)


@router.get("/ready", response_model=ReadyStatus)
async def ready() -> ReadyStatus:
    db_ok = await check_db_health()
    llm_ok = await validate_llm_connection()

    db_status = "ok" if db_ok else "unavailable"
    llm_status = "ok" if llm_ok else "unavailable"
    overall = "ok" if (db_ok and llm_ok) else "degraded"

    return ReadyStatus(status=overall, db=db_status, llm=llm_status)
