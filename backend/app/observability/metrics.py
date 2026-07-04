"""
NetPulse Backend — Prometheus-compatible metrics endpoint.

Exposes application metrics for monitoring:
- Ingestion lag per source
- API request latency (p50/p95/p99)
- Active WebSocket connections
- Incident counts by severity
- ML inference latency

Phase 8 implementation — stub for now.
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 8 — Implement metrics
# - Use prometheus_client library
# - Expose /metrics endpoint
# - Track: ingestion_lag_seconds, api_request_duration_seconds,
#   active_ws_connections, incidents_total, ml_inference_duration_seconds
