import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import anthropic

logger = logging.getLogger(__name__)

class LLMIncidentInput(BaseModel):
    incident_id: str
    affected_asn: int
    severity: str
    gnn_score: float
    latency_z_score: float
    packet_loss_z_score: float
    bgp_churn_count: int

class LLMIncidentOutput(BaseModel):
    root_cause_hypothesis: str
    confidence: str

class IncidentExplainer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def _get_fallback_explanation(self, data: LLMIncidentInput) -> str:
        """Returns a templated explanation if the LLM fails or is unavailable."""
        return (
            f"Automated root cause analysis is currently unavailable. "
            f"Incident logged via ML correlation for AS {data.affected_asn}. "
            f"Signals: GNN Score={data.gnn_score:.2f}, "
            f"BGP Churn={data.bgp_churn_count} events, "
            f"Latency Z={data.latency_z_score:.1f}, Loss Z={data.packet_loss_z_score:.1f}."
        )

    def explain(self, data: LLMIncidentInput) -> str:
        """
        Calls the Anthropic API with a strictly validated input.
        Expects a JSON response matching LLMIncidentOutput.
        """
        if not self.client:
            logger.warning("No Anthropic API key provided. Using fallback explanation.")
            return self._get_fallback_explanation(data)

        system_prompt = (
            "You are a strict, expert Tier-3 network engineer diagnostic AI. "
            "Your ONLY purpose is to analyze the provided JSON telemetry for a BGP/Latency incident "
            "and provide a 2-3 sentence root cause hypothesis. "
            "You MUST output valid JSON conforming exactly to this schema:\n"
            '{"root_cause_hypothesis": "<string>", "confidence": "<high|medium|low>"}'
        )

        user_content = data.model_dump_json()

        try:
            # Hard timeout of 5 seconds is enforced by standard client configuration if passed,
            # but we use default timeout mechanisms here wrapped in a try/except for speed.
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ],
                timeout=5.0
            )
            
            # The response.content[0].text should be JSON
            content = response.content[0].text
            
            # Strict output validation
            parsed_json = json.loads(content)
            validated_output = LLMIncidentOutput(**parsed_json)
            
            return validated_output.root_cause_hypothesis
            
        except Exception as e:
            logger.error(f"LLM Explanation failed: {e}")
            return self._get_fallback_explanation(data)
