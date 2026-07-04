"""
NetPulse — RIPE RIS Live BGP stream ingestion.

Consumes real-time BGP updates via WebSocket from
wss://ris-live.ripe.net/v1/ws/?client=netpulse

Stores announcements, withdrawals, and path changes
in the bgp_events hypertable.
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 2 — Implement RIS Live consumer
# - Establish WebSocket connection to RIS Live
# - Subscribe to BGP update messages
# - Parse and normalize BGP events
# - Batch insert into bgp_events hypertable
# - Handle reconnection on disconnect
# - Track ingestion lag metric
