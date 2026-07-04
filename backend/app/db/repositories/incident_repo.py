from typing import Sequence
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.incident import IncidentModel

class IncidentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_incidents(
        self, severity: str | None = None, active_only: bool = False, page: int = 1, size: int = 20
    ) -> tuple[Sequence[IncidentModel], int]:
        base_stmt = select(IncidentModel)
        
        if severity:
            base_stmt = base_stmt.where(IncidentModel.severity == severity)
        if active_only:
            base_stmt = base_stmt.where(IncidentModel.resolved_at.is_(None))
            
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = base_stmt.order_by(IncidentModel.detected_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_predictions(
        self, min_score: float = 0.5, page: int = 1, size: int = 20
    ) -> tuple[Sequence[IncidentModel], int]:
        base_stmt = select(IncidentModel).where(IncidentModel.prediction_score >= min_score)
        
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = base_stmt.order_by(IncidentModel.detected_at.desc()).offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_by_id(self, incident_id: UUID) -> IncidentModel | None:
        stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
