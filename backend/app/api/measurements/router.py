from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.measurements.schemas import ProbeResponse, PaginatedMeasurements
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.core.exceptions import ValidationError
from app.db.models import UserModel
from app.db.repositories.measurement_repo import MeasurementRepository

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
    repo = MeasurementRepository(session)
    probes = await repo.get_probes(country=country, asn=asn, limit=limit)
    return probes

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
        raise ValidationError("start_time must be before end_time")
        
    repo = MeasurementRepository(session)
    items, total = await repo.get_latency_time_series(
        probe_id=probe_id, 
        start_time=start_time, 
        end_time=end_time, 
        page=page, 
        size=size
    )
    
    return PaginatedMeasurements(items=items, total=total, page=page, size=size)
