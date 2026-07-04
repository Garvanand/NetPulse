from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bgp.schemas import PaginatedBGPEvents
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.core.exceptions import ValidationError
from app.db.models import UserModel
from app.db.repositories.bgp_repo import BGPRepository

router = APIRouter(prefix="/bgp", tags=["bgp"])

@router.get("/events", response_model=PaginatedBGPEvents)
async def list_bgp_events(
    start_time: datetime,
    end_time: datetime,
    prefix: str | None = Query(None, description="Exact match CIDR prefix"),
    peer_asn: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=60, window=60))
):
    """List BGP update events within a time range, optionally filtered by prefix or peer."""
    if start_time >= end_time:
        raise ValidationError("start_time must be before end_time")
        
    repo = BGPRepository(session)
    items, total = await repo.get_events(
        start_time=start_time,
        end_time=end_time,
        prefix=prefix,
        peer_asn=peer_asn,
        page=page,
        size=size
    )
    
    # Convert prefix CIDR object to string for Pydantic
    for item in items:
        if getattr(item, "prefix", None) is not None:
            item.prefix = str(item.prefix)
            
    return PaginatedBGPEvents(items=items, total=total, page=page, size=size)
