from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.models.topology import ASRelationshipModel

class TopologyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_graph(
        self, asn: int | None = None, rel_type: str | None = None, page: int = 1, size: int = 100
    ) -> tuple[Sequence[ASRelationshipModel], int]:
        base_stmt = select(ASRelationshipModel)
        
        if asn:
            base_stmt = base_stmt.where(
                or_(ASRelationshipModel.asn_a == asn, ASRelationshipModel.asn_b == asn)
            )
        if rel_type:
            base_stmt = base_stmt.where(ASRelationshipModel.rel_type == rel_type)
            
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = base_stmt.order_by(ASRelationshipModel.asn_a).offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
