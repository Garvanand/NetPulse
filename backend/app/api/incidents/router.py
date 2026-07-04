from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.incidents.schemas import IncidentResponse, PaginatedIncidents
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.core.exceptions import NotFoundError
from app.db.models import UserModel
from app.db.repositories.incident_repo import IncidentRepository

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.get("/", response_model=PaginatedIncidents)
async def list_incidents(
    severity: str | None = Query(None, description="Filter by severity (low, medium, high, critical)"),
    active_only: bool = Query(False, description="Only return unresolved incidents"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=60, window=60))
):
    """List network incidents."""
    repo = IncidentRepository(session)
    items, total = await repo.get_incidents(severity=severity, active_only=active_only, page=page, size=size)
    return PaginatedIncidents(items=items, total=total, page=page, size=size)

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=60, window=60))
):
    """Get details for a specific incident. Triggers LLM explanation if missing."""
    repo = IncidentRepository(session)
    incident = await repo.get_by_id(incident_id)
    
    if not incident:
        raise NotFoundError("Incident not found")
        
    # Lazy LLM Evaluation
    if not incident.explanation and incident.incident_metadata:
        try:
            from app.llm.explain_incident import IncidentExplainer, LLMIncidentInput
            
            # Map metadata to strict Pydantic input
            meta = incident.incident_metadata
            signals = meta.get("signals", {})
            
            llm_input = LLMIncidentInput(
                incident_id=str(incident.id),
                affected_asn=meta.get("asn", 0),
                severity=incident.severity,
                gnn_score=signals.get("gnn_score", 0.0),
                latency_z_score=signals.get("latency_z_score", 0.0),
                packet_loss_z_score=signals.get("packet_loss_z_score", 0.0),
                bgp_churn_count=signals.get("bgp_churn_count", 0)
            )
            
            explainer = IncidentExplainer()
            # This is synchronous but fast due to hard timeout
            import asyncio
            explanation = await asyncio.to_thread(explainer.explain, llm_input)
            
            incident.explanation = explanation
            await session.commit()
            await session.refresh(incident)
            
        except Exception as e:
            # We don't fail the API call if LLM fails
            import logging
            logging.error(f"Failed to generate LLM explanation: {e}")
        
    return incident
