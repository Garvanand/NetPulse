# NetPulse — Project Memory

> "Predict internet weather before it storms."

**Last Updated:** 2026-07-04
**Status:** Planning (Prompt 3 — Scope Lock)

---

## 1. Project Identity

| Field | Value |
|---|---|
| Name | NetPulse |
| Tagline | Predict internet weather before it storms |
| Type | Predictive internet path intelligence platform |
| Repo Status | Brand-new — no code exists yet |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│  Interactive World Map · AS Topology Graph · Incident Timeline   │
│  deck.gl / Mapbox · Framer Motion · TailwindCSS · Dark Mode     │
│  Deployed: Vercel / static edge                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │  REST + WebSocket
┌────────────────────────────▼─────────────────────────────────────┐
│                      BACKEND API (FastAPI)                        │
│  JWT Auth · Rate Limiting · Redis Cache (hot tiles / queries)    │
│  Single Python service, cleanly modularized (feature folders)    │
│  Deployed: Railway / Fly.io single instance                      │
├──────────────────────────────────────────────────────────────────┤
│                        ML ENGINE                                  │
│  Temporal GNN (PyTorch Geometric Temporal) — instability pred    │
│  Time-series head (lightweight Transformer / LSTM) — latency     │
│  Anomaly scorer (statistical + learned residual)                 │
│  Explanation layer: bounded Claude API call per confirmed event  │
├──────────────────────────────────────────────────────────────────┤
│                     INGESTION LAYER                               │
│  Celery / APScheduler scheduled jobs                              │
│  RIPE Atlas measurements · RIS Live BGP stream                   │
│  Periodic CAIDA graph refresh · RouteViews MRT parsing           │
│  Cloudflare Radar corroboration                                  │
├──────────────────────────────────────────────────────────────────┤
│                     STORAGE LAYER                                 │
│  PostgreSQL + TimescaleDB (hypertables for time-series)          │
│  Graph tables (adjacency in Postgres; Neo4j optional later)      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources — Verification Status

### 3.1 RIPE Atlas API ✅ VERIFIED
- **What:** Active measurement network — ping / traceroute / DNS from 12,000+ global probes.
- **Access:** Free RIPE NCC Access account → API key. No limit on key count.
- **Rate Limits:** 300 req/s general, 150 req/s measurement API. HTTP 429 on excess.
- **Credit System:** Reading existing public measurements is free. Creating custom measurements costs credits (earned by hosting a probe or being an NCC member).
- **Streaming:** Streaming API available for real-time results (preferred over polling).
- **Archives:** Bulk historical data available via FTP at `ftp.ripe.net/ripe/atlas/probes/archive/`.
- **Terms:** Standard RIPE NCC Terms of Service.
- **MVP Impact:** Use existing public built-in measurements only (no credit spend needed).

### 3.2 RIPE RIS Live / RIS Raw Dumps ✅ VERIFIED
- **What:** Real-time and historical BGP update streams from RIPE route collectors.
- **Access:** Publicly available, **no authentication required** (may change in future).
- **Endpoint:** `wss://ris-live.ripe.net/v1/ws/`
- **Identification:** Recommended `?client=netpulse` parameter for debugging support.
- **Limits:** Connections may be closed if client can't keep up with data volume.
- **Commercial Use:** Requires branding/attribution per RIS Commercial Use Terms.
- **Terms:** RIPE NCC Website and Publicly Available Services ToS.

### 3.3 RouteViews (University of Oregon) ✅ VERIFIED
- **What:** BGP RIB snapshots (every ~2 hours) and update archives (every 15 min) in MRT format.
- **Access:** Publicly and freely accessible via HTTP, FTP, and rsync.
- **Archive URL:** `http://archive.routeviews.org/`
- **API:** REST API available at `https://api.routeviews.org/docs/`.
- **Parsing Tools:** bgpdump, BGPKIT (Rust + Python bindings), CAIDA BGPStream, mrtparse.
- **Terms:** Open access, no authentication required.

### 3.4 CAIDA AS Relationships Dataset ✅ VERIFIED
- **What:** AS-to-AS relationship graph (customer / peer / provider).
- **Access:** Publicly accessible under CAIDA Acceptable Use Agreement (AUA).
- **Series:** `serial-1` (BGP-inferred), `serial-2` (BGP + Ark traceroute + multilateral peering).
- **Updates:** Ongoing, files available through 2025–2026.
- **Terms:** Free for research/education. Requires:
  1. Citation: "The CAIDA AS Relationships Dataset, <date range> https://www.caida.org/catalog/datasets/as-relationships/"
  2. Notification to CAIDA on publication via their reporting form or `data-info@caida.org`.
- **Commercial Use:** Allowed under AUA with attribution, but verify full AUA text before any commercial deployment.

### 3.5 Cloudflare Radar API ✅ VERIFIED
- **What:** Global internet traffic, outage signals, routing data — used as corroborating signal.
- **Access:** Free to use across all plans. API key required.
- **Rate Limits:** 1,200 requests per 5-minute window per API token. HTTP 429 on excess.
- **License:** CC BY-NC 4.0 (non-commercial). **⚠ Important: if NetPulse is ever commercialized, Cloudflare Radar data cannot be used directly; it would need to be dropped or re-licensed.**
- **Terms:** Cloudflare API Terms of Service.

---

## 4. Hard Constraints

| Constraint | Detail |
|---|---|
| **No Docker / Kubernetes** | Single deployable Python service + static/edge-deployed Next.js frontend |
| **No microservice sprawl** | One backend service, cleanly modularized (repository pattern, feature folders) |
| **No large always-on LLM** | Claude API calls are rare, bounded (1 per confirmed incident), and cached |
| **Deployment target** | Vercel (frontend) + Railway / Fly.io single instance (backend) |
| **Single developer** | All decisions should minimize operational complexity |

---

## 5. Key Technology Choices

| Layer | Technology | Rationale |
|---|---|---|
| Backend | FastAPI (Python) | Async, fast, great for WebSocket + REST |
| Task Scheduling | APScheduler (primary) or Celery + Redis | APScheduler simpler for single-instance |
| Database | PostgreSQL + TimescaleDB | Time-series hypertables, mature, single-instance friendly |
| Cache | Redis | Hot map tiles, query caching, rate limiting backend |
| ML — Graph | PyTorch Geometric Temporal | Temporal GNN over AS graph snapshots |
| ML — Time-series | Lightweight Transformer or LSTM | Per-probe latency trend forecasting |
| ML — Anomaly | Statistical + learned residual | Z-score / MAD baseline + neural residual |
| MRT Parsing | BGPKIT (Rust + Python bindings) | High-performance MRT parsing |
| BGP Streaming | WebSocket client to RIS Live | Native async compatibility with FastAPI |
| LLM | Claude API (Anthropic) | Bounded explanation calls only |
| Frontend | Next.js + TypeScript + TailwindCSS | SSR, modern DX, edge-deployable |
| Map | deck.gl or Mapbox GL JS | WebGL-accelerated geospatial visualization |
| Animation | Framer Motion | Smooth UI transitions |

---

## 6. Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-04 | All 5 data sources verified accessible | Web research confirms current availability |
| 2026-07-04 | APScheduler preferred over Celery for MVP | No separate worker process needed for single-instance |
| 2026-07-04 | Cloudflare Radar flagged CC BY-NC 4.0 | Must drop or re-license before any commercialization |
| 2026-07-04 | CAIDA requires citation + pub notification | Added to compliance checklist |
| 2026-07-04 | Custom Atlas measurements need credits | MVP will use existing public measurements only |

---

## 7. Open Questions

1. **Mapbox vs. deck.gl:** Mapbox requires an API token and has usage-based pricing. deck.gl is fully open-source. Decide during frontend implementation.
2. **Neo4j vs. Postgres adjacency:** Start with Postgres adjacency lists; benchmark before adding Neo4j.
3. **Claude API cost budget:** Define a monthly cap for explanation calls. Cache aggressively.
4. **CAIDA AUA commercial clause:** If NetPulse is ever commercialized, review full AUA text with legal counsel.
