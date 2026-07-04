"""
NetPulse Backend — Pydantic response/request schemas for the API.

These schemas define the API contract between backend and frontend.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Probes ──────────────────────────────────────────────────────────


class ProbeResponse(BaseModel):
    """A RIPE Atlas probe with location and status."""

    probe_id: int
    asn: int | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None

    model_config = {"from_attributes": True}


class ProbeListResponse(BaseModel):
    """Paginated list of probes."""

    probes: list[ProbeResponse]
    total: int


# ── Measurements ────────────────────────────────────────────────────


class MeasurementPoint(BaseModel):
    """A single measurement data point."""

    time: datetime
    rtt_ms: float | None = None
    packet_loss: float | None = None

    model_config = {"from_attributes": True}


class TimeSeriesResponse(BaseModel):
    """Time series data for a probe or AS."""

    probe_id: int
    points: list[MeasurementPoint]


# ── AS (Autonomous System) ──────────────────────────────────────────


class ASDetailResponse(BaseModel):
    """Detailed information about an Autonomous System."""

    asn: int
    name: str | None = None
    org: str | None = None
    country: str | None = None
    cone_size: int | None = None
    current_anomaly_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Current anomaly score (0.0–1.0)"
    )
    current_instability_score: float | None = Field(
        None, ge=0.0, le=1.0, description="GNN-predicted instability (0.0–1.0)"
    )
    neighbor_count: int | None = None

    model_config = {"from_attributes": True}


class ASRelationshipResponse(BaseModel):
    """An edge in the AS topology graph."""

    asn_a: int
    asn_b: int
    rel_type: str  # 'customer', 'peer', 'provider'

    model_config = {"from_attributes": True}


class TopologyResponse(BaseModel):
    """AS topology subgraph for visualization."""

    nodes: list[ASDetailResponse]
    edges: list[ASRelationshipResponse]


# ── Incidents ───────────────────────────────────────────────────────


class IncidentResponse(BaseModel):
    """A detected or predicted internet incident."""

    id: UUID
    detected_at: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    incident_type: str  # 'latency_spike', 'bgp_hijack', 'route_leak', 'outage'
    affected_asns: list[int] | None = None
    prediction_score: float | None = Field(None, ge=0.0, le=1.0)
    explanation: str | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    incidents: list[IncidentResponse]
    total: int
    page: int
    page_size: int


# ── Map ─────────────────────────────────────────────────────────────


class MapProbePoint(BaseModel):
    """A probe point for map rendering (lightweight)."""

    probe_id: int
    lat: float
    lng: float
    status: str | None = None
    anomaly_score: float | None = None


class MapIncidentOverlay(BaseModel):
    """An incident overlay for the map."""

    id: UUID
    lat: float
    lng: float
    severity: str
    incident_type: str
    affected_asns: list[int] | None = None


class MapDataResponse(BaseModel):
    """Combined map data: probes + incidents."""

    probes: list[MapProbePoint]
    incidents: list[MapIncidentOverlay]


# ── WebSocket ───────────────────────────────────────────────────────


class WSMessage(BaseModel):
    """WebSocket message envelope."""

    type: str  # 'incident', 'measurement', 'prediction', 'heartbeat'
    timestamp: datetime
    data: dict[str, Any]
