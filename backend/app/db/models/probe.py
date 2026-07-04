from datetime import datetime
from sqlalchemy import Column, DateTime, Double, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base

class ProbeModel(Base):
    """RIPE Atlas probe registry (cached). Normalized table (not a hypertable)."""

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
    This table MUST be converted to a TimescaleDB hypertable on `time`.
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
        # Essential for latency time-series queries
        Index("ix_probe_measurements_probe_time", "probe_id", "time"),
        Index("ix_probe_measurements_asn_src", "asn_src"),
        Index("ix_probe_measurements_asn_dst", "asn_dst"),
    )
