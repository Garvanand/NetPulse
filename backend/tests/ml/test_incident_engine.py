import pytest
from app.ml.incident_engine import IncidentEngine

def test_incident_engine_critical_cascade():
    """True Positive: High ML score + Stats + BGP = Critical Incident"""
    engine = IncidentEngine()
    decision = engine.evaluate(
        asn=123,
        gnn_score=0.95,
        latency_z_score=4.0,
        packet_loss_z_score=0.0,
        bgp_churn=20
    )
    
    assert decision.should_raise is True
    assert decision.severity == "critical"
    assert decision.metadata["triggers"]["gnn"] is True
    assert decision.metadata["triggers"]["statistical"] is True
    assert decision.metadata["triggers"]["bgp"] is True

def test_incident_engine_warning_only():
    """True Negative: GNN suspects something but stats are normal = No Incident"""
    engine = IncidentEngine()
    decision = engine.evaluate(
        asn=456,
        gnn_score=0.90,
        latency_z_score=1.0,
        packet_loss_z_score=0.5,
        bgp_churn=5
    )
    
    assert decision.should_raise is False
    assert decision.metadata["triggers"]["gnn"] is True
    assert decision.metadata["triggers"]["statistical"] is False

def test_incident_engine_traditional_outage():
    """True Positive: No ML suspicion but stats and BGP correlate = Medium Incident"""
    engine = IncidentEngine()
    decision = engine.evaluate(
        asn=789,
        gnn_score=0.20,
        latency_z_score=5.0,
        packet_loss_z_score=10.0,
        bgp_churn=50
    )
    
    assert decision.should_raise is True
    assert decision.severity == "medium"
    assert decision.metadata["triggers"]["gnn"] is False
    assert decision.metadata["triggers"]["statistical"] is True
