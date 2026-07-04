"""
NetPulse — ML anomaly scorer.

Statistical + learned residual anomaly detection.
Phase 3 implementation.
"""

import structlog

logger = structlog.get_logger()


# TODO: Phase 3 — Implement anomaly detection
# - Per-probe Z-score / Median Absolute Deviation on RTT and packet loss
# - Per-AS BGP churn rate vs. rolling baseline
# - Composite anomaly score (0.0–1.0) per probe/AS per time window
# - Neural residual model (learns from statistical baseline errors)
