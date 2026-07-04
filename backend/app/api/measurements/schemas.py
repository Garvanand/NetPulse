from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProbeResponse(BaseModel):
    probe_id: int
    asn: int | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)

class LatencyMeasurementResponse(BaseModel):
    time: datetime
    probe_id: int
    target_ip: str | None = None
    rtt_ms: float | None = None
    packet_loss: float | None = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedMeasurements(BaseModel):
    items: list[LatencyMeasurementResponse]
    total: int
    page: int
    size: int
