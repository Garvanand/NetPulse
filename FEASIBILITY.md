# NetPulse — Feasibility Assessment

**Date:** 2026-07-04
**Verdict:** ✅ FEASIBLE with defined scope-down path

---

## 1. Data Source Verification Summary

| Source | Status | Access | Rate Limits | License Risk |
|---|---|---|---|---|
| RIPE Atlas API | ✅ Verified | Free account + API key | 300 req/s general, 150 req/s measurement | None (reading public data) |
| RIPE RIS Live | ✅ Verified | No auth required (WebSocket) | Connection closed if client can't keep up | Commercial use requires attribution |
| RouteViews | ✅ Verified | Public HTTP/FTP/rsync, no auth | None (static file archives) | None (open access) |
| CAIDA AS Rel | ✅ Verified | Public under AUA | None (file download) | Requires citation + pub notification |
| Cloudflare Radar | ✅ Verified | Free API key | 1,200 req / 5 min | **CC BY-NC 4.0 — non-commercial only** |

> **No data source claims are marked as ASSUMPTION.** All five were verified via web research on 2026-07-04.

---

## 2. Risk Register

### RISK 1: GNN Training Data Volume
**Severity:** HIGH | **Likelihood:** MEDIUM

The temporal GNN needs aligned graph snapshots with per-AS node features. Building sufficient training data requires:
- 30–90 days of continuous ingestion before meaningful training
- Feature coverage: not all ASes will have probe measurements (RIPE Atlas covers ~12K probes, but not all ~75K ASes)

**Mitigations:**
- Cold-start with statistical anomaly detection (Phase 3) — works from day 1, no training needed
- Backfill historical data from RIPE Atlas archives + RouteViews MRT dumps
- Use BGP churn features (available for all ASes via RIS/RouteViews) as primary node features; latency features are supplementary
- Start GNN training on MVP subgraph (see Risk 3) after 30 days of collection

### RISK 2: Rate Limits & API Quotas
**Severity:** MEDIUM | **Likelihood:** LOW

RIPE Atlas: 300 req/s is generous for a single-instance application. Cloudflare Radar: 1,200 req / 5 min = 4 req/s, sufficient for 15-min polling.

**Mitigations:**
- Use RIPE Atlas Streaming API instead of polling REST
- Cache all API responses in Redis with appropriate TTLs
- Use RIPE Atlas archives for bulk historical data instead of API
- Implement exponential backoff + circuit breaker on all external API calls
- Cloudflare Radar is a corroboration signal; temporary unavailability is non-critical

### RISK 3: Full Internet Graph Scale
**Severity:** HIGH | **Likelihood:** HIGH

The global AS topology has ~75,000 ASes and ~300,000+ edges. Running a temporal GNN over this on a single GPU (Railway/Fly.io instance) may be infeasible in terms of memory and compute.

**Mitigations:**
- **MVP Subgraph Strategy:**
  1. **Tier 1 (2,000 ASes):** Top transit providers by customer cone size — covers backbone where most incidents propagate
  2. **Tier 2 (5,000 ASes):** Tier 1 + their direct customer/peer ASes — captures propagation paths
  3. **Tier 3 (full graph):** Only if Tier 2 succeeds and compute budget allows
- Graph sampling techniques: neighbor sampling, subgraph batching (supported by PyG)
- Pre-compute embeddings offline, serve predictions from cache
- Use lighter GNN variants (GraphSAGE with sampling) if full-batch training is too expensive

### RISK 4: Data Freshness & Alignment
**Severity:** MEDIUM | **Likelihood:** MEDIUM

Different sources update at different rates:
- RIS Live: real-time (seconds)
- RIPE Atlas built-in measurements: ~5 min intervals
- RouteViews MRT: 15 min archives
- CAIDA: monthly/quarterly releases

Temporal misalignment between measurement data and graph topology could introduce noise into GNN training.

**Mitigations:**
- Align all data to fixed time windows (e.g., 1-hour snapshots for GNN, 5-min for anomaly detection)
- Use the most recent CAIDA graph as "current topology" — AS relationships change slowly (days/weeks)
- For real-time anomaly detection, use streaming data directly (no alignment needed)
- GNN predictions are medium-term (1–4 hours ahead), so moderate lag is acceptable

### RISK 5: Cloudflare Radar CC BY-NC 4.0 License
**Severity:** LOW (for now) | **Likelihood:** N/A

Cloudflare Radar data is licensed CC BY-NC 4.0. This prohibits commercial use of the data.

**Mitigations:**
- Cloudflare Radar is a corroboration signal, not a primary data source — it can be dropped entirely
- If commercialization is planned, remove Cloudflare Radar integration or negotiate a separate license
- All core functionality (anomaly detection, GNN predictions, incident detection) works without Cloudflare Radar

### RISK 6: Claude API Cost & Availability
**Severity:** LOW | **Likelihood:** LOW

Explanation calls are bounded (1 per confirmed incident), but costs could grow during major outage events (multiple simultaneous incidents).

**Mitigations:**
- Cache explanations per incident (never regenerate)
- Rate limit to max 10 explanation calls per hour
- Set monthly spend cap on Anthropic API account
- Degrade gracefully: show structured incident data without explanation if API is unavailable or budget exhausted
- Batch related incidents before calling (e.g., if 5 ASes in the same upstream go down, explain once)

---

## 3. MVP Scope-Down Path

If the full system proves too ambitious, here is a progressive scope-down strategy:

### MVP-0: "Internet Weather Dashboard" (2–3 weeks)
- **Data:** RIPE Atlas public measurements + RIPE RIS Live only
- **ML:** Statistical anomaly detection only (Z-score on RTT + BGP churn rate)
- **Backend:** FastAPI with REST endpoints, no WebSocket yet
- **Frontend:** Static map showing probe locations, anomaly heatmap, incident list
- **No GNN, no Claude, no RouteViews, no Cloudflare Radar**

### MVP-1: "Predictive Layer" (+2–3 weeks)
- Add time-series forecasting (LSTM) for per-probe latency
- Add CAIDA topology graph + basic AS graph visualization
- Add WebSocket for live updates
- Add RouteViews MRT ingestion for richer BGP data

### MVP-2: "Intelligence Layer" (+3–4 weeks)
- Add Temporal GNN on MVP subgraph (top 2,000 transit ASes)
- Add Claude explanation calls for confirmed incidents
- Add Cloudflare Radar corroboration
- Add incident timeline with historical playback

### MVP-3: "Production Polish" (+2 weeks)
- Observability (metrics, logging, health checks)
- JWT auth + rate limiting
- Deploy to Vercel + Railway/Fly.io
- Performance optimization (query caching, tile pre-computation)

---

## 4. Compute & Infrastructure Requirements

| Resource | MVP-0 | MVP-2 (Full) |
|---|---|---|
| **Backend CPU** | 1 vCPU | 2–4 vCPU |
| **Backend RAM** | 1 GB | 4–8 GB |
| **GPU** | None | Optional (training only; can use Colab/Lambda) |
| **PostgreSQL** | 10 GB | 50–100 GB (with 90 days retention) |
| **Redis** | 256 MB | 512 MB–1 GB |
| **Estimated Monthly Cost** | $15–25 | $50–100 |

> GPU is needed only for GNN training, which can be done offline on Google Colab, Lambda, or a local machine. Inference is CPU-friendly for a 2K-node subgraph.

---

## 5. Timeline Estimate

| Phase | Duration | Cumulative |
|---|---|---|
| Foundation (P1) | 3–4 days | Week 1 |
| Data Pipeline (P2) | 5–7 days | Week 2 |
| ML Baseline (P3) | 5–7 days | Week 3 |
| Backend API (P5) | 4–5 days | Week 4 |
| Frontend MVP (P6) | 5–7 days | Week 5 |
| ML GNN (P4) | 7–10 days | Week 6–7 |
| Integration (P7) | 5–7 days | Week 8 |
| Observability + Deploy (P8–9) | 3–5 days | Week 9 |

**Total estimate: 8–9 weeks** for the full system (single developer, full-time).
**MVP-0 can be demonstrated in ~2 weeks.**

---

## 6. Go / No-Go Recommendation

| Criterion | Assessment |
|---|---|
| Data availability | ✅ All 5 sources verified and accessible |
| Technical feasibility | ✅ All components have proven implementations |
| Scale concerns | ⚠️ Manageable with MVP subgraph strategy |
| Cost | ✅ $50–100/mo for full system, $15–25/mo for MVP |
| Licensing | ⚠️ Cloudflare Radar is NC-only; droppable if needed |
| Single-developer scope | ⚠️ Ambitious but achievable with progressive MVPs |

### **Verdict: GO** — proceed to Phase 1 (Foundation) with the understanding that:
1. Statistical anomaly detection ships first (no ML training delay)
2. GNN trains on a 2K-AS subgraph (not full internet)
3. Cloudflare Radar is a nice-to-have, not a dependency
4. Claude explanation calls are bounded and cached
