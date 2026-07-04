from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.api.topology.schemas import PaginatedTopology
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.db.models import ASRelationshipModel, UserModel

router = APIRouter(prefix="/topology", tags=["topology"])

@router.get("/as-graph", response_model=PaginatedTopology)
async def get_as_graph(
    asn: int | None = Query(None, description="Filter relationships involving this ASN"),
    rel_type: str | None = Query(None, description="Filter by customer, provider, or peer"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=30, window=60))
):
    """Retrieve AS relationships for the global topology graph."""
    base_stmt = select(ASRelationshipModel)
    
    if asn:
        base_stmt = base_stmt.where(
            or_(ASRelationshipModel.asn_a == asn, ASRelationshipModel.asn_b == asn)
        )
    if rel_type:
        base_stmt = base_stmt.where(ASRelationshipModel.rel_type == rel_type)
        
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    
    stmt = base_stmt.order_by(ASRelationshipModel.asn_a).offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    
    return PaginatedTopology(items=items, total=total, page=page, size=size)
