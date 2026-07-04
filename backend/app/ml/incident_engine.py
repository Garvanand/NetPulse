from typing import Dict, Any, List, Optional
import numpy as np
from pydantic import BaseModel

class IncidentDecision(BaseModel):
    should_raise: bool
    severity: str
    metadata: Dict[str, Any]

class IncidentEngine:
    """
    Decides whether a raw ML prediction and statistical anomalies 
    constitute a confirmed incident.
    """
    
    def __init__(
        self, 
        gnn_threshold: float = 0.85,
        z_score_threshold: float = 3.0,
        bgp_churn_threshold: int = 15
    ):
        """
        Tunable thresholds for incident detection.
        - gnn_threshold: The raw sigmoid output from the Temporal GNN (0.0 to 1.0)
        - z_score_threshold: Deviations from the moving average for latency/loss.
        - bgp_churn_threshold: Number of BGP withdraws/announces to be considered a routing event.
        """
        self.gnn_threshold = gnn_threshold
        self.z_score_threshold = z_score_threshold
        self.bgp_churn_threshold = bgp_churn_threshold

    def evaluate(
        self, 
        asn: int, 
        gnn_score: float, 
        latency_z_score: float, 
        packet_loss_z_score: float,
        bgp_churn: int
    ) -> IncidentDecision:
        """
        Evaluates signals and returns a decision.
        """
        # Rule 1: The ML model is highly confident (e.g., detected a topology cascade)
        gnn_trigger = gnn_score >= self.gnn_threshold
        
        # Rule 2: There is a statistically significant active degradation
        stat_trigger = (latency_z_score >= self.z_score_threshold) or (packet_loss_z_score >= self.z_score_threshold)
        
        # Rule 3: There is corresponding routing instability
        bgp_trigger = bgp_churn >= self.bgp_churn_threshold
        
        should_raise = False
        severity = "low"
        
        # Decision Matrix
        if gnn_trigger and stat_trigger and bgp_trigger:
            should_raise = True
            severity = "critical"
        elif gnn_trigger and stat_trigger:
            should_raise = True
            severity = "high"
        elif stat_trigger and bgp_trigger:
            # Traditional non-ML heuristic
            should_raise = True
            severity = "medium"
        elif gnn_trigger:
            # GNN suspects something but stats haven't spiked yet. 
            # We don't raise an active incident to avoid alert fatigue, 
            # but we could log a warning.
            should_raise = False
            
        metadata = {
            "asn": asn,
            "signals": {
                "gnn_score": float(gnn_score),
                "latency_z_score": float(latency_z_score),
                "packet_loss_z_score": float(packet_loss_z_score),
                "bgp_churn_count": int(bgp_churn)
            },
            "triggers": {
                "gnn": gnn_trigger,
                "statistical": stat_trigger,
                "bgp": bgp_trigger
            }
        }
        
        return IncidentDecision(
            should_raise=should_raise,
            severity=severity,
            metadata=metadata
        )
