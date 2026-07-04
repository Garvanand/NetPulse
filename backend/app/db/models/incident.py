import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Double, Index, String, Text, Integer
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class IncidentModel(Base):
    """Detected or predicted internet incidents."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'low', 'medium', 'high', 'critical'
    incident_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # 'latency_spike', 'bgp_hijack', 'route_leak', 'outage'
    affected_asns = Column(ARRAY(Integer), nullable=True)
    affected_prefixes = Column(ARRAY(CIDR), nullable=True)
    prediction_score: Mapped[float | None] = mapped_column(Double, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    incident_metadata = Column(JSONB, nullable=True)
