import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from redis.asyncio import Redis

from app.api.topology.schemas import PaginatedTopology
from app.core.dependencies import get_db_session, get_redis
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
    redis: Redis | None = Depends(get_redis),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=30, window=60))
):
    """Retrieve AS relationships for the global topology graph."""
    
    # 1. Check Cache
    cache_key = f"netpulse:cache:topology:{asn}:{rel_type}:{page}:{size}"
    if redis:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
            
    # 2. Database Query
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
    
    # We must construct a dict matching the schema so we can serialize to JSON for caching
    # because Pydantic models aren't directly JSON serializable via standard json.dumps
    items = []
    for rel in result.scalars().all():
        items.append({
            "asn_a": rel.asn_a,
            "asn_b": rel.asn_b,
            "rel_type": rel.rel_type
        })
        
    response_data = {
        "items": items,
        "total": total,
        "page": page,
        "size": size
    }
    
    # 3. Set Cache (TTL 24 hours, as topology rarely changes)
    if redis:
        await redis.setex(cache_key, 86400, json.dumps(response_data))
        
    return response_data
