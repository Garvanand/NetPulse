"""
NetPulse — RouteViews MRT archive ingestion.

Downloads and parses BGP RIB snapshots and update archives
from http://archive.routeviews.org/ in MRT format.

Uses BGPKIT parser (Rust + Python bindings) for high-performance parsing.
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 2 — Implement RouteViews ingestion
# - Discover latest MRT dump files from archive index
# - Download MRT files (updates every 15 min, RIBs every 2 hours)
# - Parse with bgpkit-parser
# - Extract and store BGP events in bgp_events hypertable
# - Deduplicate against RIS Live events
