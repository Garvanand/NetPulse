from datetime import datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.probe import ProbeModel, ProbeMeasurementModel

class MeasurementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_probes(self, country: str | None = None, limit: int = 100) -> Sequence[ProbeModel]:
        stmt = select(ProbeModel)
        if country:
            stmt = stmt.where(ProbeModel.country == country.upper())
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latency_time_series(
        self, probe_id: int, start_time: datetime, end_time: datetime, page: int = 1, size: int = 50
    ) -> tuple[Sequence[ProbeMeasurementModel], int]:
        base_stmt = select(ProbeMeasurementModel).where(
            ProbeMeasurementModel.probe_id == probe_id,
            ProbeMeasurementModel.time >= start_time,
            ProbeMeasurementModel.time <= end_time
        )
        
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        
        stmt = base_stmt.order_by(ProbeMeasurementModel.time.desc()).offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
