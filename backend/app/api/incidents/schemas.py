from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict

class IncidentResponse(BaseModel):
    id: UUID
    detected_at: datetime
    severity: str
    incident_type: str
    affected_asns: list[int] | None = None
    prediction_score: float | None = None
    explanation: str | None = None
    resolved_at: datetime | None = None
    incident_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedIncidents(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    size: int
