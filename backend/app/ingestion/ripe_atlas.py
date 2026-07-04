"""
NetPulse — RIPE Atlas API ingestion.

Fetches public built-in measurements (ping, traceroute, DNS) from the
RIPE Atlas REST API and stores results in the probe_measurements table.

MVP: Read-only access to existing public measurements (no credit spend).
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 2 — Implement RIPE Atlas ingestion
# - Fetch built-in measurement IDs for ping/traceroute
# - Poll latest results via REST API (or Streaming API)
# - Parse and store in probe_measurements hypertable
# - Fetch and cache probe metadata (location, ASN, country)
