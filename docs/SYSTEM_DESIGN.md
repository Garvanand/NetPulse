# NetPulse — System Design

> Conceptual design document covering data model, API contract style,
> and component responsibilities, reflecting the final implemented state.

**Status:** Locked as of 2026-07-04

---

## 1. System Overview

NetPulse is a **predictive internet path intelligence platform** that ingests
real-time and historical internet routing/measurement data, applies statistical
and graph-neural-network-based analysis, and surfaces predictions of internet
instability through a rich interactive frontend.

### Core Loop

```
Observe → Store → Analyze → Predict → Explain → Visualize
```

1. **Observe** — Continuously ingest BGP updates, active probe measurements,
   and AS topology data via custom ingestion clients (RIPE Atlas, RIS Live, RouteViews, CAIDA).
2. **Store** — Persist time-series measurement data and BGP events in
   **TimescaleDB hypertables**; maintain an AS relationship graph in relational
   adjacency tables.
3. **Analyze** — Run statistical anomaly detection on structured
   data; compute BGP churn rates and latency Z-scores.
4. **Predict** — A temporal GNN processes graph snapshots to forecast per-AS instability. ML inference runs inside an `asyncio.to_thread` pool to prevent blocking the FastAPI event loop.
5. **Explain** — When an incident is confirmed, an asynchronous call to the **Anthropic Claude API** generates a 2–3 sentence natural-language root-cause hypothesis from a strict JSON context.
6. **Visualize** — The Next.js frontend renders an interactive world map (Deck.GL), a 3D AS topology graph, incident timelines, and heatmaps.

---

## 2. Conceptual Data Model

### 2.1 Design Rationale & Graph Strategy

| Table | Storage Strategy | Why |
|---|---|---|
| `probe_measurements` | TimescaleDB hypertable | High-volume append-only writes. Queries dominant on time ranges. |
| `bgp_events` | TimescaleDB hypertable | Very high volume BGP stream. Windowed aggregations for churn rate. |
| `as_relationships` | Relational Adjacency | Updated daily from CAIDA. Indexed joins satisfy our neighborhood and graph serialization queries. See [ADR-0002](adr/0002-graph-storage-strategy.md). |
| `incidents` | Standard Postgres | Low volume; stores metadata arrays and cached LLM explanations (JSONB). |

---

## 3. API Contract Style

### 3.1 REST API

- **Convention:** JSON:API-inspired, strongly-typed via Pydantic.
- **Versioning:** URL path prefix `/api/v1/`
- **Authentication:** JWT bearer tokens in `Authorization` header. Bcrypt hashing with 12 rounds.
- **Error Format:** Centralized Domain Exceptions yielding `{ "error": { "code": 400, "message": "..." } }`
- **Caching:** Expensive routes (like `/api/v1/topology/as-graph`) are backed by a **Redis Cache** (dropping p95 latency to <18ms).
- **Architecture**: Enforces the **Repository Pattern**. Routers interact strictly with Repositories (`IncidentRepository`, etc.), fully decoupling HTTP transport from SQL syntax.

### 3.2 WebSocket Contract

A single WebSocket endpoint at `/ws/live` multiplexes message types:
Expects a JWT token in the query params for authentication.

---

## 4. Component Responsibilities

### 4.1 Ingestion Layer (Implemented)

| Component | Responsibility |
|---|---|
| `ripe_atlas_client.py` | Poll public built-in measurements via REST API |
| `ripe_ris_client.py` | Consume BGP updates via RIS Live |
| `routeviews_client.py` | Download + parse MRT archives |
| `caida_loader.py` | Download + parse AS relationship dataset |

### 4.2 ML Engine

| Component | Responsibility |
|---|---|
| `gnn_model.py` / `inference.py` | Custom PyTorch Temporal GNN instability prediction. Offloaded to background threads. |
| `incident_engine.py` | Correlates GNN anomaly scores with latency and BGP churn thresholds. |
| `explain_incident.py` | Invokes the Claude LLM with a strictly bounded Pydantic prompt for root-cause synthesis. |

### 4.3 Backend API

| Component | Responsibility |
|---|---|
| `routes/incidents.py` | Incident CRUD + lazy evaluation of LLM explanations. |
| `routes/topology.py` | Redis-cached AS graph subgraph endpoint. |
| `routes/measurements.py` | Per-probe latency history. |
| `core/exceptions.py` | Global exception hierarchy. |
| `db/repositories/` | Decoupled SQLAlchemy database layer. |

### 4.4 Frontend

| Component | Responsibility |
|---|---|
| `map/` | `next/dynamic` lazy-loaded WebGL deck.gl interactive world map. |
| `topology/` | AS topology graph visualization. |
| `lib/api-client.ts` | Centralized typed HTTP fetch wrapper handling JWT injection. |

---

## 5. Security Model

- **Authentication:** JWT tokens signed with HS256. 
- **Rate Limiting:** Redis-backed sliding window counter. Default: 60 requests/minute.
- **LLM Boundaries:** Claude API is heavily restricted to a single-shot completion on internal JSON states. No open-ended chat interface exists. See [ADR-0004](adr/0004-llm-usage-boundary.md).
