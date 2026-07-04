from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.incidents.schemas import IncidentResponse, PaginatedIncidents
from app.core.dependencies import get_db_session
from app.core.security import get_current_active_user
from app.core.rate_limit import RateLimiter
from app.db.models import IncidentModel, UserModel

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
    base_stmt = select(IncidentModel)
    
    if severity:
        base_stmt = base_stmt.where(IncidentModel.severity == severity)
    if active_only:
        base_stmt = base_stmt.where(IncidentModel.resolved_at.is_(None))
        
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    
    stmt = base_stmt.order_by(IncidentModel.detected_at.desc()).offset((page - 1) * size).limit(size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    
    return PaginatedIncidents(items=items, total=total, page=page, size=size)

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user: UserModel = Depends(get_current_active_user),
    rate_limit: None = Depends(RateLimiter(requests=60, window=60))
):
    """Get details for a specific incident. Triggers LLM explanation if missing."""
    stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
    result = await session.execute(stmt)
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
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
            explanation = explainer.explain(llm_input)
            
            incident.explanation = explanation
            await session.commit()
            await session.refresh(incident)
            
        except Exception as e:
            # We don't fail the API call if LLM fails
            import logging
            logging.error(f"Failed to generate LLM explanation: {e}")
        
    return incident
