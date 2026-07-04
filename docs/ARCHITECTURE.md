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
    end

    subgraph Ingestion Layer
        RA -->|REST poll| ING_ATLAS[ripe_atlas_client.py]
        RL -->|WebSocket stream| ING_RIS[ripe_ris_client.py]
        RV -->|HTTP download| ING_RV[routeviews_client.py]
        CA -->|HTTP download| ING_CA[caida_loader.py]
    end

    subgraph Storage Layer
        ING_ATLAS -->|INSERT| PM[(probe_measurements<br/>TimescaleDB hypertable)]
        ING_ATLAS -->|UPSERT| PR[(probes<br/>registry cache)]
        ING_RIS -->|INSERT| BGP[(bgp_events<br/>TimescaleDB hypertable)]
        ING_RV -->|INSERT| BGP
        ING_CA -->|UPSERT| ASR[(as_relationships<br/>adjacency table)]
        ING_CA -->|UPSERT| ASM[(as_metadata<br/>enrichment)]
    end

    subgraph ML Engine
        PM -->|feature query| FE[Feature Engineering<br/>5-min / 1-hour windows]
        BGP -->|churn rate| FE
        ASR -->|graph structure| FE

        FE -->|graph snapshots| GNN[Temporal GNN<br/>Custom PyTorch GConvGRU]

        FE -->|per-probe stats| DET[Incident Engine<br/>latency + BGP + GNN thresholds]
        GNN -->|instability scores| DET

        DET -->|confirmed incident| EXP[Explainer<br/>Claude API bounded call]
        DET -->|INSERT| INC[(incidents<br/>Standard Postgres)]
        EXP -->|UPDATE explanation| INC
    end

    subgraph Backend API - FastAPI
        INC -->|query| API_INC[/api/v1/incidents]
        PM -->|query| API_TS[/api/v1/measurements]
        PR -->|query| API_MAP[/api/v1/measurements/probes]
        ASR -->|query| API_TOPO[/api/v1/topology]
        BGP -->|query| API_BGP[/api/v1/bgp]

        API_TOPO --> CACHE[(Redis Cache)]
    end

    subgraph Frontend - Next.js
        API_MAP -->|REST| MAP[World Map<br/>deck.gl]
        API_TOPO -->|REST| GRAPH[AS Topology<br/>force-directed graph]
        API_INC -->|REST| TIMELINE[Incident Timeline<br/>filterable list]
    end
```

---

## 2. Component Architecture (Detail)

### 2.1 Storage Layer

```text
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
│  │    • users, api_keys                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                         Redis 7+                             │ │
│  │                                                              │ │
│  │  Caching:                                                    │ │
│  │    • Topology subgraph (TTL: 5min) drops latency to <20ms    │ │
│  │                                                              │ │
│  │  Rate Limiting:                                              │ │
│  │    • Sliding window counters per authenticated user          │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 ML Engine

The machine learning engine deviates slightly from the original architecture documentation to prioritize operational stability and avoid event-loop blocking:

- **GNN Implementation**: Instead of importing `PyTorch Geometric Temporal`, we built a custom `GConvGRU` in `app/ml/gnn_model.py`. This reduces massive binary dependency weight and cross-platform compilation issues (especially on Windows).
- **Concurrency**: ML Inference is explicitly offloaded to `asyncio.to_thread`. Tensor multiplications are synchronous CPU-bound operations that would otherwise stall FastAPI's main event loop.
- **Incident Engine**: Acts as a hard boundary between statistical noise and LLM invocations. We do not invoke the LLM unless the Temporal GNN score AND Z-Score threshold are both breached concurrently.

### 2.3 Backend API (FastAPI)

The backend enforces the **Repository Pattern**. Route handlers never see SQLAlchemy syntax. They inject the DB session into a Repository (e.g. `IncidentRepository`), which yields Pydantic-compliant models.

Errors are handled via a centralized Exception Hierarchy (`NetPulseException`) which guarantees a consistent JSON format: `{"error": {"code": 404, "message": "Not Found"}}`.

### 2.4 Frontend (Next.js)

Uses `next/dynamic` extensively to lazy-load massive WebGL bundles (`deck.gl`, `react-force-graph-3d`) ensuring the initial JavaScript payload remains small and TTI is fast. All API requests route through a strongly-typed `apiClient` singleton that manages JWT injection.

---

## 3. ADR Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](adr/0001-database-choice.md) | Database Choice: PostgreSQL + TimescaleDB | Accepted |
| [ADR-0002](adr/0002-graph-storage-strategy.md) | Graph Storage: Postgres Adjacency over Neo4j | Accepted |
| [ADR-0003](adr/0003-ml-framework-choice.md) | ML Framework: PyTorch Geometric Temporal | Accepted *(Implementation diverged to Custom GConvGRU for stability)* |
| [ADR-0004](adr/0004-llm-usage-boundary.md) | LLM Usage Boundary: Explanation Only | Accepted |
| [ADR-0005](adr/0005-deployment-strategy-no-docker.md) | Deployment: No Docker, Single-Service | Accepted |
