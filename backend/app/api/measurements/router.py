from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.measurements.schemas import ProbeResponse, PaginatedMeasurements
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.db.models import ProbeModel, ProbeMeasurementModel, UserModel

router = APIRouter(prefix="/measurements", tags=["measurements"])

@router.get("/probes", response_model=list[ProbeResponse])
async def list_probes(
    country: str | None = Query(None, min_length=2, max_length=2),
    asn: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=100, window=60))
):
    """List and query active RIPE Atlas probes."""
    stmt = select(ProbeModel)
    if country:
        stmt = stmt.where(ProbeModel.country == country.upper())
    if asn:
        stmt = stmt.where(ProbeModel.asn == asn)
        
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/{probe_id}/latency", response_model=PaginatedMeasurements)
async def get_probe_latency(
    probe_id: int,
    start_time: datetime,
    end_time: datetime,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=60, window=60))
):
    """Get time-series latency data for a specific probe."""
    if start_time >= end_time:
        raise HTTPException(status_code=422, detail="start_time must be before end_time")
        
    base_stmt = select(ProbeMeasurementModel).where(
        ProbeMeasurementModel.probe_id == probe_id,
        ProbeMeasurementModel.time >= start_time,
        ProbeMeasurementModel.time <= end_time
    )
    
    # Count total
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    
    # Fetch paginated
    stmt = base_stmt.order_by(ProbeMeasurementModel.time.desc()).offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    
    return PaginatedMeasurements(items=items, total=total, page=page, size=size)
