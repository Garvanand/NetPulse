"""
NetPulse — Explanation layer (Claude API).

Generates natural-language root-cause hypotheses for confirmed incidents.
One bounded API call per incident, results are cached.

Constraints:
- Max 10 calls per hour (configurable)
- Cache TTL: 24 hours
- Never used for anything except incident explanation
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 7 — Implement Claude explanation layer
# - Accept structured incident JSON (affected ASes, probes, BGP events, magnitude)
# - Single Claude API call → 2–3 sentence root-cause hypothesis
# - Cache explanation in incidents.explanation column
# - Rate limit: max claude_max_calls_per_hour per hour
# - Batch related incidents before calling
# - Graceful degradation: serve raw incident data if API unavailable
