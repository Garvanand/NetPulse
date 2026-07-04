# NetPulse — Technical Architecture

> Locked as of 2026-07-04. Changes require ADR amendment.

**Components:** 6 (Ingestion · Storage · ML Engine · Backend API · Frontend · Observability)

---

## 1. Full System Data Flow

```mermaid
graph TB
    subgraph External Data Sources
        RA[RIPE Atlas API<br/>ping/traceroute/DNS<br/>12K+ probes]
        RL[RIPE RIS Live<br/>BGP WebSocket stream<br/>real-time updates]
        RV[RouteViews<br/>MRT archive dumps<br/>15-min intervals]
        CA[CAIDA Dataset<br/>AS relationships<br/>serial-2 graph]
        CF[Cloudflare Radar<br/>traffic/outage signals<br/>corroboration]
    end

    subgraph Ingestion Layer
        RA -->|REST poll 5min| ING_ATLAS[ripe_atlas.py<br/>APScheduler job]
        RL -->|WebSocket stream| ING_RIS[ris_live.py<br/>async consumer]
        RV -->|HTTP download 15min| ING_RV[routeviews.py<br/>BGPKIT parser]
        CA -->|HTTP download daily| ING_CA[caida.py<br/>relationship parser]
        CF -->|REST poll 15min| ING_CF[cloudflare_radar.py<br/>outage poller]
    end

    subgraph Storage Layer
        ING_ATLAS -->|INSERT| PM[(probe_measurements<br/>TimescaleDB hypertable)]
        ING_ATLAS -->|UPSERT| PR[(probes<br/>registry cache)]
        ING_RIS -->|INSERT| BGP[(bgp_events<br/>TimescaleDB hypertable)]
        ING_RV -->|INSERT| BGP
        ING_CA -->|UPSERT| ASR[(as_relationships<br/>adjacency table)]
        ING_CA -->|UPSERT| ASM[(as_metadata<br/>enrichment)]
        ING_CF -->|UPDATE| INC[(incidents<br/>corroboration)]
    end

    subgraph ML Engine
        PM -->|feature query| FE[Feature Engineering<br/>5-min / 1-hour windows]
        BGP -->|churn rate| FE
        ASR -->|graph structure| FE

        FE -->|per-probe stats| ANOM[Anomaly Scorer<br/>Z-score + MAD]
        FE -->|RTT time series| TS[Time-Series Head<br/>LSTM / Transformer]
        FE -->|graph snapshots| GNN[Temporal GNN<br/>PyG Temporal RGCN]

        ANOM -->|anomaly scores| DET[Incident Detector<br/>threshold + corroboration]
        TS -->|predicted RTT| DET
        GNN -->|instability scores| DET

        DET -->|confirmed incident| EXP[Explainer<br/>Claude API bounded call]
        DET -->|INSERT| INC
        EXP -->|UPDATE explanation| INC
    end

    subgraph Backend API - FastAPI
        INC -->|query| API_INC[/api/v1/incidents]
        PM -->|query| API_TS[/api/v1/timeseries]
        PR -->|query| API_MAP[/api/v1/map/probes]
        ASR -->|query| API_TOPO[/api/v1/topology]
        ASM -->|query| API_AS[/api/v1/as/asn]

        API_INC --> CACHE[(Redis Cache)]
        API_MAP --> CACHE
        API_TOPO --> CACHE

        DET -->|push| WS[WebSocket /ws/live]
    end

    subgraph Frontend - Next.js
        API_MAP -->|REST| MAP[World Map<br/>deck.gl]
        API_TOPO -->|REST| GRAPH[AS Topology<br/>force-directed graph]
        API_INC -->|REST| TIMELINE[Incident Timeline<br/>filterable list]
        API_AS -->|REST| DETAIL[AS Detail View<br/>latency + predictions]
        API_TS -->|REST| CHART[Latency Charts<br/>time-series plots]
        WS -->|WebSocket| LIVE[Live Updates<br/>real-time overlays]
    end

    subgraph Observability
        API_INC -.->|structured logs| LOG[structlog<br/>JSON / console]
        API_INC -.->|metrics| MET[/metrics<br/>Prometheus format]
        API_INC -.->|status| HEALTH[/health<br/>dependency checks]
    end
```

---

## 2. Component Architecture (Detail)

### 2.1 Ingestion Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                             │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ APScheduler  │  │  Async WS   │  │     Periodic Jobs        │ │
│  │  (in-proc)   │  │  Consumer   │  │                          │ │
│  │              │  │              │  │  RouteViews: 15 min      │ │
│  │  Atlas: 5min │  │  RIS Live:  │  │  CAIDA:     24 hours     │ │
│  │  CF Radar:   │  │  continuous │  │                          │ │
│  │    15min     │  │              │  │                          │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘ │
│         │                 │                       │               │
│         ▼                 ▼                       ▼               │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Batch Writer (asyncpg bulk INSERT)              │ │
│  │                                                              │ │
│  │  • Buffer incoming records in memory (configurable batch     │ │
│  │    size: 100–1000 rows)                                      │ │
│  │  • Flush on batch full OR timer (every 5 seconds)            │ │
│  │  • ON CONFLICT DO NOTHING for deduplication                  │ │
│  │  • Track ingestion_lag_seconds metric per source             │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- APScheduler runs **in-process** (no separate Celery worker) — see [ADR-0005](adr/0005-deployment-strategy-no-docker.md)
- RIS Live WebSocket consumer runs as an **asyncio background task** within the FastAPI lifespan
- Batch writer amortizes INSERT cost over many rows
- Each ingestion module is a self-contained feature folder with its own parsing logic

### 2.2 Storage Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                PostgreSQL 16 + TimescaleDB                   │ │
│  │                                                              │ │
│  │  Hypertables (auto-partitioned by time):                     │ │
│  │    • probe_measurements — 7-day chunk interval               │ │
│  │    • bgp_events — 1-day chunk interval (higher volume)       │ │
│  │                                                              │ │
│  │  Standard tables:                                            │ │
│  │    • probes, as_relationships, as_metadata, incidents        │ │
│  │                                                              │ │
│  │  Retention policies:                                         │ │
│  │    • 90-day drop policy on hypertables                       │ │
│  │    • Continuous aggregates for hourly/daily rollups           │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                         Redis 7+                             │ │
│  │                                                              │ │
│  │  Caching:                                                    │ │
│  │    • Map probe data (TTL: 30s)                               │ │
│  │    • Active incidents (TTL: 15s)                              │ │
│  │    • Topology subgraph (TTL: 5min)                           │ │
│  │    • Incident explanations (TTL: 24h)                        │ │
│  │                                                              │ │
│  │  Rate Limiting:                                              │ │
│  │    • Sliding window counters per API key                     │ │
│  │                                                              │ │
│  │  Pub/Sub:                                                    │ │
│  │    • WebSocket broadcast channel (if multi-instance later)   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 ML Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML ENGINE                                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Feature Engineering Pipeline                                │ │
│  │                                                              │ │
│  │  Scheduled: every 5 minutes (anomaly), every 1 hour (GNN)   │ │
│  │                                                              │ │
│  │  1. Query time-windowed aggregates from hypertables          │ │
│  │  2. Compute per-probe: mean_rtt, p95_rtt, packet_loss       │ │
│  │  3. Compute per-AS: bgp_churn_rate, announcement_count      │ │
│  │  4. Aggregate probe features to AS level                    │ │
│  │  5. Join with structural features (degree, cone_size)        │ │
│  │  6. Build graph snapshot: adjacency + node feature matrix    │ │
│  └──────────────┬────────────────────┬─────────────────┬────────┘ │
│                 │                    │                  │          │
│                 ▼                    ▼                  ▼          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐ │
│  │  Anomaly Scorer   │ │ Time-Series Head │ │  Temporal GNN      │ │
│  │                    │ │                  │ │                    │ │
│  │  • Z-score / MAD  │ │  • LSTM (2-layer)│ │  • RGCN layers     │ │
│  │  • Per-probe      │ │  • 5-min inputs  │ │  • GRU recurrence  │ │
│  │  • Per-AS churn   │ │  • 15/30/60 min  │ │  • 1-hour snapshots│ │
│  │  • Rolling window │ │    forecast      │ │  • 1–4 hour pred   │ │
│  │  • No training    │ │  • 30-day train  │ │  • 30–90 day train │ │
│  │    needed         │ │                  │ │  • MVP: 2K AS nodes│ │
│  └────────┬─────────┘ └────────┬─────────┘ └──────────┬─────────┘ │
│           │                    │                       │           │
│           ▼                    ▼                       ▼           │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Incident Detector                                           │ │
│  │                                                              │ │
│  │  Rules:                                                      │ │
│  │  1. anomaly_score > 0.8 → create LOW incident               │ │
│  │  2. anomaly + prediction_corroboration → MEDIUM              │ │
│  │  3. Multiple ASes affected → HIGH                            │ │
│  │  4. Backbone AS (high cone_size) + prolonged → CRITICAL      │ │
│  │  5. Cloudflare Radar confirms → escalate severity            │ │
│  └──────────────────────────┬───────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Explainer (Claude API)                                      │ │
│  │                                                              │ │
│  │  • Triggered: ONLY on confirmed incidents (score ≥ MEDIUM)   │ │
│  │  • Input: structured JSON (affected ASes, probes, BGP events,│ │
│  │    magnitude, timeline)                                      │ │
│  │  • Output: 2–3 sentence root-cause hypothesis                │ │
│  │  • Constraints: max 10 calls/hour, 24h cache, never for     │ │
│  │    detection/prediction — see ADR-0004                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Backend API (FastAPI)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI)                          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Middleware    │  │  JWT Auth    │  │   Rate Limiter         │  │
│  │              │  │              │  │   (Redis sliding       │  │
│  │ • CORS       │  │ • Token      │  │    window)             │  │
│  │ • Logging    │  │   validation │  │                        │  │
│  │ • Metrics    │  │ • API keys   │  │   60 req/min default   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬─────────────┘  │
│         │                 │                      │                │
│         ▼                 ▼                      ▼                │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Route Handlers                            │ │
│  │                                                              │ │
│  │  REST:                                                       │ │
│  │    GET  /health                     (no auth)                │ │
│  │    GET  /api/v1/map/probes          (auth required)          │ │
│  │    GET  /api/v1/map/incidents       (auth required)          │ │
│  │    GET  /api/v1/as/{asn}            (auth required)          │ │
│  │    GET  /api/v1/as/{asn}/predictions(auth required)          │ │
│  │    GET  /api/v1/incidents           (auth required)          │ │
│  │    GET  /api/v1/incidents/{id}      (auth required)          │ │
│  │    GET  /api/v1/topology            (auth required)          │ │
│  │    GET  /api/v1/timeseries/{pid}    (auth required)          │ │
│  │                                                              │ │
│  │  WebSocket:                                                  │ │
│  │    WS   /ws/live                    (token in query param)   │ │
│  └──────────────────────────┬───────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │               Repository Layer                               │ │
│  │                                                              │ │
│  │  ProbeRepo · MeasurementRepo · BGPEventRepo                 │ │
│  │  ASGraphRepo · IncidentRepo                                  │ │
│  │                                                              │ │
│  │  • Typed async methods                                       │ │
│  │  • Routes never touch SQLAlchemy directly                    │ │
│  │  • Upsert with ON CONFLICT for idempotent writes             │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Frontend (Next.js)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16+)                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  App Router Pages                                            │ │
│  │                                                              │ │
│  │  /              → Dashboard (Map View — default)             │ │
│  │  /as/[asn]      → AS Detail View                             │ │
│  │  /topology      → AS Topology Graph                          │ │
│  │  /incidents     → Incident Timeline                          │ │
│  │  /settings      → API Key Management                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Map Layer    │  │ Graph Layer  │  │  Data Layer            │  │
│  │              │  │              │  │                        │  │
│  │ deck.gl      │  │ react-force- │  │  • API client (httpx)  │  │
│  │ ScatterLayer │  │   graph-3d   │  │  • useWebSocket hook   │  │
│  │ HeatmapLayer │  │              │  │  • SWR / React Query   │  │
│  │ ArcLayer     │  │ Nodes colored│  │  • TypeScript types    │  │
│  │              │  │ by instability│  │                        │  │
│  └──────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                   │
│  Design: TailwindCSS · Framer Motion · Dark Mode (default)       │
│  Deploy: Vercel (edge/static)                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 Observability

```
┌─────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY                               │
│                                                                   │
│  Structured Logging (structlog)                                  │
│    • JSON format in production                                   │
│    • Colored console in development                              │
│    • Key events: ingestion_batch, ml_inference, incident_created │
│                                                                   │
│  Metrics (Prometheus-compatible /metrics endpoint)               │
│    • ingestion_lag_seconds{source="ripe_atlas"}                  │
│    • bgp_events_ingested_total                                   │
│    • ml_inference_duration_seconds{model="gnn"}                  │
│    • api_request_duration_seconds{endpoint="/api/v1/map/probes"} │
│    • active_ws_connections                                       │
│    • incidents_total{severity="high"}                            │
│                                                                   │
│  Health (/health endpoint)                                       │
│    • database: connection + query test                           │
│    • redis: ping test                                            │
│    • data_freshness: last ingestion timestamp per source         │
│    • ml_status: last inference timestamp per model               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Deployment Architecture

```
┌────────────────────────┐        ┌────────────────────────────┐
│       Vercel CDN        │        │  Railway / Fly.io          │
│                         │        │  (single instance)         │
│  Next.js static/SSR     │  REST  │                            │
│  frontend               │◄──────►│  FastAPI backend           │
│                         │  + WS  │  + APScheduler (in-proc)   │
│  Edge-cached            │        │  + ML inference (CPU)      │
│                         │        │                            │
└────────────────────────┘        └───────────┬────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                    ┌────▼────┐         ┌─────▼─────┐       ┌─────▼─────┐
                    │ Postgres │         │   Redis   │       │   Claude  │
                    │ + Timescale│       │  (Upstash/ │       │   API     │
                    │ (Timescale │       │  Railway)  │       │(Anthropic)│
                    │  Cloud /   │       │            │       │           │
                    │  Railway)  │       │  256MB–1GB │       │  Bounded  │
                    │            │       │            │       │  ≤10/hr   │
                    │  10–100 GB │       └────────────┘       └───────────┘
                    └────────────┘

   No Docker. No Kubernetes. No multi-service orchestration.
   See ADR-0005 for rationale.
```

**GNN Training** (offline, not part of the deployed service):
- Run on Google Colab, Lambda Cloud, or local GPU
- Export trained model weights (`.pt` file)
- Upload to backend; inference runs on CPU

---

## 4. Cross-Cutting Concerns

### 4.1 Configuration

All configuration via environment variables with `NETPULSE_` prefix,
managed by pydantic-settings. A `.env.example` documents all variables.

### 4.2 Error Handling

- All external API calls wrapped in circuit breakers (exponential backoff)
- Database errors: retry with backoff; log and continue for non-critical writes
- ML inference errors: log and serve stale predictions from cache
- LLM errors: serve incident without explanation text

### 4.3 Data Attribution

Required attributions built into the codebase:
- CAIDA: citation in `README.md` + API response headers
- RIPE RIS: `?client=netpulse` on WebSocket connections
- Cloudflare Radar: CC BY-NC 4.0 attribution in UI footer

---

## 5. ADR Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](adr/0001-database-choice.md) | Database Choice: PostgreSQL + TimescaleDB | Accepted |
| [ADR-0002](adr/0002-graph-storage-strategy.md) | Graph Storage: Postgres Adjacency over Neo4j | Accepted |
| [ADR-0003](adr/0003-ml-framework-choice.md) | ML Framework: PyTorch Geometric Temporal | Accepted |
| [ADR-0004](adr/0004-llm-usage-boundary.md) | LLM Usage Boundary: Explanation Only | Accepted |
| [ADR-0005](adr/0005-deployment-strategy-no-docker.md) | Deployment: No Docker, Single-Service | Accepted |
