"""
NetPulse Backend — Repository pattern for data access.

Provides typed, async repository classes that encapsulate database queries.
All SQL is behind repository methods; routes never touch SQLAlchemy directly.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ASMetadataModel,
    ASRelationshipModel,
    BGPEventModel,
    IncidentModel,
    ProbeMeasurementModel,
    ProbeModel,
)

logger = structlog.get_logger()


class ProbeRepository:
    """Data access for RIPE Atlas probes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_probes(self, probes: list[dict]) -> int:
        """Bulk upsert probes. Returns count of upserted rows."""
        if not probes:
            return 0

        stmt = pg_insert(ProbeModel).values(probes)
        stmt = stmt.on_conflict_do_update(
            index_elements=["probe_id"],
            set_={
                "asn": stmt.excluded.asn,
                "country": stmt.excluded.country,
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
                "status": stmt.excluded.status,
                "updated_at": datetime.now(UTC),
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_all_probes(self, status: str | None = None) -> Sequence[ProbeModel]:
        """Fetch all probes, optionally filtered by status."""
        query = select(ProbeModel)
        if status:
            query = query.where(ProbeModel.status == status)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_probes_by_asn(self, asn: int) -> Sequence[ProbeModel]:
        """Fetch all probes in a given AS."""
        result = await self.session.execute(
            select(ProbeModel).where(ProbeModel.asn == asn)
        )
        return result.scalars().all()


class MeasurementRepository:
    """Data access for probe measurements (TimescaleDB hypertable)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_measurements(self, measurements: list[dict]) -> int:
        """Bulk insert measurements. Returns count of inserted rows."""
        if not measurements:
            return 0

        stmt = pg_insert(ProbeMeasurementModel).values(measurements)
        stmt = stmt.on_conflict_do_nothing()  # Skip duplicates (same time + probe_id)
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_latest_by_probe(
        self, probe_id: int, limit: int = 100
    ) -> Sequence[ProbeMeasurementModel]:
        """Get most recent measurements for a specific probe."""
        result = await self.session.execute(
            select(ProbeMeasurementModel)
            .where(ProbeMeasurementModel.probe_id == probe_id)
            .order_by(ProbeMeasurementModel.time.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_asn_timerange(
        self,
        asn: int,
        start: datetime,
        end: datetime,
    ) -> Sequence[ProbeMeasurementModel]:
        """Get measurements for an AS within a time range (source or destination)."""
        result = await self.session.execute(
            select(ProbeMeasurementModel)
            .where(
                (ProbeMeasurementModel.asn_src == asn)
                | (ProbeMeasurementModel.asn_dst == asn),
                ProbeMeasurementModel.time >= start,
                ProbeMeasurementModel.time <= end,
            )
            .order_by(ProbeMeasurementModel.time)
        )
        return result.scalars().all()


class BGPEventRepository:
    """Data access for BGP events (TimescaleDB hypertable)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_events(self, events: list[dict]) -> int:
        """Bulk insert BGP events. Returns count of inserted rows."""
        if not events:
            return 0

        stmt = pg_insert(BGPEventModel).values(events)
        stmt = stmt.on_conflict_do_nothing()
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_churn_rate(
        self, asn: int, start: datetime, end: datetime
    ) -> int:
        """Count BGP events involving an AS in a time window (churn rate)."""
        result = await self.session.execute(
            select(func.count())
            .select_from(BGPEventModel)
            .where(
                BGPEventModel.origin_asn == asn,
                BGPEventModel.time >= start,
                BGPEventModel.time <= end,
            )
        )
        return result.scalar() or 0


class ASGraphRepository:
    """Data access for AS topology (relationships + metadata)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_relationships(self, relationships: list[dict]) -> int:
        """Bulk upsert AS relationships from CAIDA."""
        if not relationships:
            return 0

        stmt = pg_insert(ASRelationshipModel).values(relationships)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asn_a", "asn_b"],
            set_={
                "rel_type": stmt.excluded.rel_type,
                "source": stmt.excluded.source,
                "updated_at": datetime.now(UTC),
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def get_neighbors(self, asn: int) -> Sequence[ASRelationshipModel]:
        """Get all AS relationships involving a given ASN."""
        result = await self.session.execute(
            select(ASRelationshipModel).where(
                (ASRelationshipModel.asn_a == asn)
                | (ASRelationshipModel.asn_b == asn)
            )
        )
        return result.scalars().all()

    async def get_full_graph(self) -> Sequence[ASRelationshipModel]:
        """Fetch the entire AS relationship graph. Use with caution on large datasets."""
        result = await self.session.execute(select(ASRelationshipModel))
        return result.scalars().all()

    async def upsert_metadata(self, metadata_list: list[dict]) -> int:
        """Bulk upsert AS metadata."""
        if not metadata_list:
            return 0

        stmt = pg_insert(ASMetadataModel).values(metadata_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asn"],
            set_={
                "name": stmt.excluded.name,
                "org": stmt.excluded.org,
                "country": stmt.excluded.country,
                "cone_size": stmt.excluded.cone_size,
                "updated_at": datetime.now(UTC),
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]


class IncidentRepository:
    """Data access for detected/predicted incidents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_incident(self, incident: dict) -> IncidentModel:
        """Create a new incident record."""
        model = IncidentModel(**incident)
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_active_incidents(
        self, limit: int = 50
    ) -> Sequence[IncidentModel]:
        """Get active (unresolved) incidents, ordered by severity and recency."""
        result = await self.session.execute(
            select(IncidentModel)
            .where(IncidentModel.resolved_at.is_(None))
            .order_by(IncidentModel.detected_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_incident_by_id(self, incident_id: UUID) -> IncidentModel | None:
        """Get a single incident by ID."""
        result = await self.session.execute(
            select(IncidentModel).where(IncidentModel.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def update_explanation(self, incident_id: UUID, explanation: str) -> None:
        """Cache a Claude-generated explanation on an incident."""
        await self.session.execute(
            update(IncidentModel)
            .where(IncidentModel.id == incident_id)
            .values(explanation=explanation)
        )

    async def resolve_incident(self, incident_id: UUID) -> None:
        """Mark an incident as resolved."""
        await self.session.execute(
            update(IncidentModel)
            .where(IncidentModel.id == incident_id)
            .values(resolved_at=datetime.now(UTC))
        )
