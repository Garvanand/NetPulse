"""
NetPulse — Cloudflare Radar API ingestion.

Fetches internet traffic and outage signals from the Cloudflare Radar API
as a corroborating signal for anomaly detection.

License: CC BY-NC 4.0 (non-commercial use only).
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 2 (P2 priority) — Implement Cloudflare Radar poller
# - Fetch outage detection signals
# - Fetch traffic anomaly data by country/AS
# - Store as corroboration metadata (JSONB in incidents or separate table)
# - Rate limit: 1,200 req / 5 min
