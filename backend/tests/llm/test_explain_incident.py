import pytest
import os
from unittest.mock import patch, MagicMock
from app.llm.explain_incident import IncidentExplainer, LLMIncidentInput, LLMIncidentOutput

@pytest.fixture
def mock_input():
    return LLMIncidentInput(
        incident_id="test-123",
        affected_asn=3356,
        severity="critical",
        gnn_score=0.98,
        latency_z_score=5.2,
        packet_loss_z_score=0.1,
        bgp_churn_count=45
    )

def test_fallback_no_api_key(mock_input):
    """If no API key is present, fallback is used."""
    # Ensure no environment variable
    with patch.dict(os.environ, clear=True):
        explainer = IncidentExplainer(api_key="")
        explanation = explainer.explain(mock_input)
        
    assert "Automated root cause analysis is currently unavailable" in explanation
    assert "3356" in explanation

@patch("anthropic.Anthropic")
def test_successful_llm_call(mock_anthropic_class, mock_input):
    """A schema-valid JSON response is correctly parsed."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"root_cause_hypothesis": "A massive BGP route leak occurred.", "confidence": "high"}')]
    
    mock_client.messages.create.return_value = mock_response
    
    explainer = IncidentExplainer(api_key="mock_key")
    # Manually inject the mocked client
    explainer.client = mock_client
    
    explanation = explainer.explain(mock_input)
    assert explanation == "A massive BGP route leak occurred."

@patch("anthropic.Anthropic")
def test_failed_llm_call_fallback(mock_anthropic_class, mock_input):
    """If the LLM returns invalid JSON or times out, fallback is triggered."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    mock_client.messages.create.side_effect = Exception("Timeout or 500 error")
    
    explainer = IncidentExplainer(api_key="mock_key")
    explainer.client = mock_client
    
    explanation = explainer.explain(mock_input)
    assert "Automated root cause analysis is currently unavailable" in explanation
