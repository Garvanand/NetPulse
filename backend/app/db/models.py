"""
NetPulse Backend — SQLAlchemy models for PostgreSQL + TimescaleDB.

These models define the core data schema:
- ProbeModel: RIPE Atlas probe registry
- ProbeMeasurementModel: time-series latency/loss (TimescaleDB hypertable)
- BGPEventModel: BGP announcements/withdrawals (TimescaleDB hypertable)
- ASRelationshipModel: AS-to-AS topology from CAIDA
- ASMetadataModel: AS names, orgs, countries
- IncidentModel: detected/predicted incidents
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Double,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class ProbeModel(Base):
    """RIPE Atlas probe registry (cached)."""

    __tablename__ = "probes"

    probe_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asn: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class ProbeMeasurementModel(Base):
    """
    Time-series probe measurement data.
    This table is converted to a TimescaleDB hypertable on `time`.
    """

    __tablename__ = "probe_measurements"

    # Composite PK: (time, probe_id) for hypertable compatibility
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    probe_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    target_ip = Column(INET, nullable=True)
    measurement_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rtt_ms: Mapped[float | None] = mapped_column(Double, nullable=True)
    packet_loss: Mapped[float | None] = mapped_column(Double, nullable=True)
    asn_src: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asn_dst: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country_src: Mapped[str | None] = mapped_column(String(2), nullable=True)
    country_dst: Mapped[str | None] = mapped_column(String(2), nullable=True)
    raw_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_probe_measurements_probe_time", "probe_id", "time"),
        Index("ix_probe_measurements_asn_src", "asn_src"),
        Index("ix_probe_measurements_asn_dst", "asn_dst"),
    )


class BGPEventModel(Base):
    """
    BGP event data from RIS Live and RouteViews.
    This table is converted to a TimescaleDB hypertable on `time`.
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


class ASRelationshipModel(Base):
    """AS-to-AS relationship graph from CAIDA dataset."""

    __tablename__ = "as_relationships"

    asn_a: Mapped[int] = mapped_column(Integer, primary_key=True)
    asn_b: Mapped[int] = mapped_column(Integer, primary_key=True)
    rel_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'customer', 'peer', 'provider'
    source: Mapped[str] = mapped_column(String(30), default="caida-serial2")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("ix_as_relationships_asn_b", "asn_b"),
    )


class ASMetadataModel(Base):
    """AS metadata: names, organizations, countries."""

    __tablename__ = "as_metadata"

    asn: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    cone_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


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

class UserModel(Base):
    """Registered users for API access."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
