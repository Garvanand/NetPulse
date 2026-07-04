"""
NetPulse Backend — Health check endpoint.

Reports application health including database and Redis connectivity,
and data source freshness metrics.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_db_session, get_redis

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


@router.get("/health", response_model=dict[str, Any])
async def health_check(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis | None = Depends(get_redis),
) -> dict[str, Any]:
    """
    Application health check.

    Returns overall status plus individual dependency checks:
    - database: PostgreSQL + TimescaleDB connectivity
    - redis: Redis connectivity
    """
    settings = get_settings()
    checks: dict[str, dict[str, Any]] = {}
    overall_healthy = True

    # ── Database check ───────────────────────────────────────────
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
        logger.error("health_check_db_failed", error=str(e))

    # ── Redis check ──────────────────────────────────────────────
    if redis is not None:
        try:
            pong = await redis.ping()
            checks["redis"] = {"status": "healthy" if pong else "unhealthy"}
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False
            logger.error("health_check_redis_failed", error=str(e))
    else:
        checks["redis"] = {"status": "unavailable", "note": "Redis not configured"}

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get("/")
async def root() -> dict[str, str]:
    """Root endpoint — service identity."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "tagline": "Predict internet weather before it storms.",
    }
