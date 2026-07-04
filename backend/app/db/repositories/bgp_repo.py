from datetime import datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.bgp import BGPEventModel

class BGPRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_events(
        self, start_time: datetime, end_time: datetime, prefix: str | None = None, peer_asn: int | None = None, page: int = 1, size: int = 50
    ) -> tuple[Sequence[BGPEventModel], int]:
        base_stmt = select(BGPEventModel).where(
            BGPEventModel.time >= start_time,
            BGPEventModel.time <= end_time
        )
        if prefix:
            from sqlalchemy import String
            base_stmt = base_stmt.where(BGPEventModel.prefix.cast(String) == prefix)
        if peer_asn:
            base_stmt = base_stmt.where(BGPEventModel.peer_asn == peer_asn)
            
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = base_stmt.order_by(BGPEventModel.time.desc()).offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
