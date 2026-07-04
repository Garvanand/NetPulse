import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class BGPEventModel(Base):
    """
    BGP event data from RIS Live and RouteViews.
    This table MUST be converted to a TimescaleDB hypertable on `time`.
    """

    __tablename__ = "bgp_events"

    # Composite PK for hypertable: (time, id)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collector: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    prefix = Column(CIDR, nullable=True)
    peer_asn: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    origin_asn: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    as_path = Column(ARRAY(Integer), nullable=True)
    communities = Column(ARRAY(Integer, dimensions=2), nullable=True)
    raw_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_bgp_events_origin_time", "origin_asn", "time"),
    )
