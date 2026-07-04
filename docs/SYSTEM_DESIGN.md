# NetPulse — System Design

> Conceptual design document covering data model, API contract style,
> and component responsibilities. Implementation details (DDL, OpenAPI spec)
> are deferred to later prompts.

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
   and AS topology data from 5 verified external sources.
2. **Store** — Persist time-series measurement data and BGP events in
   TimescaleDB hypertables; maintain an AS relationship graph in relational
   adjacency tables.
3. **Analyze** — Run statistical anomaly detection (Z-score, MAD) on streaming
   data in real-time; compute per-AS BGP churn rates against rolling baselines.
4. **Predict** — A temporal GNN processes periodic graph snapshots (AS topology
   + node features) to forecast per-AS instability 1–4 hours ahead; a
   lightweight LSTM/Transformer forecasts per-probe latency trends.
5. **Explain** — When an incident is confirmed (anomaly + prediction
   corroboration), a single bounded Claude API call generates a 2–3 sentence
   natural-language root-cause hypothesis from structured JSON context.
6. **Visualize** — The Next.js frontend renders an interactive world map with
   probe overlays, AS topology graph, incident timeline, and prediction
   confidence heatmaps.

---

## 2. Conceptual Data Model

### 2.1 Table Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TIME-SERIES TABLES                           │
│               (TimescaleDB hypertables, partitioned on `time`)      │
│                                                                     │
│  ┌─────────────────────────┐   ┌─────────────────────────────────┐  │
│  │   probe_measurements    │   │          bgp_events             │  │
│  │                         │   │                                 │  │
│  │  time (PK, partition)   │   │  time (PK, partition)           │  │
│  │  probe_id (PK)          │   │  id (PK, UUID)                  │  │
│  │  target_ip              │   │  collector                      │  │
│  │  measurement_type       │   │  event_type                     │  │
│  │  rtt_ms                 │   │  prefix (CIDR)                  │  │
│  │  packet_loss            │   │  peer_asn, origin_asn           │  │
│  │  asn_src, asn_dst       │   │  as_path (INTEGER[])            │  │
│  │  country_src/dst        │   │  communities                    │  │
│  │  raw_json (JSONB)       │   │  raw_json (JSONB)               │  │
│  └─────────────────────────┘   └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         GRAPH TABLES                                │
│                 (Standard relational, adjacency list)                │
│                                                                     │
│  ┌─────────────────────────┐   ┌─────────────────────────────────┐  │
│  │    as_relationships     │   │         as_metadata             │  │
│  │                         │   │                                 │  │
│  │  asn_a (PK)             │   │  asn (PK)                       │  │
│  │  asn_b (PK)             │   │  name, org, country             │  │
│  │  rel_type               │   │  cone_size                      │  │
│  │  source                 │   │  updated_at                     │  │
│  │  updated_at             │   │                                 │  │
│  └─────────────────────────┘   └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       ENTITY TABLES                                 │
│                                                                     │
│  ┌─────────────────────────┐   ┌─────────────────────────────────┐  │
│  │         probes          │   │          incidents              │  │
│  │                         │   │                                 │  │
│  │  probe_id (PK)          │   │  id (PK, UUID)                  │  │
│  │  asn, country           │   │  detected_at, resolved_at       │  │
│  │  latitude, longitude    │   │  severity, incident_type        │  │
│  │  status                 │   │  affected_asns, affected_pfxs   │  │
│  │  updated_at             │   │  prediction_score               │  │
│  │                         │   │  explanation (cached LLM text)   │  │
│  │                         │   │  metadata (JSONB)                │  │
│  └─────────────────────────┘   └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Design Rationale

| Table | Storage Strategy | Why |
|---|---|---|
| `probe_measurements` | TimescaleDB hypertable on `time` | High-volume append-only writes (~12K probes × every 5 min); automatic chunk management; time-range queries dominant |
| `bgp_events` | TimescaleDB hypertable on `time` | Very high volume BGP stream (~1K events/sec during convergence); time-windowed aggregations for churn rate |
| `as_relationships` | Standard Postgres table | Updated daily from CAIDA; ~300K rows; adjacency queries via indexed joins; no time partitioning needed |
| `as_metadata` | Standard Postgres table | Small (~75K rows); enrichment join target; infrequently updated |
| `probes` | Standard Postgres table | Cached probe registry (~12K rows); point lookups by probe_id or spatial queries |
| `incidents` | Standard Postgres table | Low volume (tens per day); complex queries with filters; stores cached LLM explanations |

### 2.3 Graph Storage Strategy

The AS topology graph is stored as a **relational adjacency list** in the
`as_relationships` table, not in a dedicated graph database.

**Query patterns supported:**
- Get all neighbors of an AS: `WHERE asn_a = ? OR asn_b = ?`
- Get full graph for GNN snapshot: `SELECT * FROM as_relationships`
- Get subgraph for visualization: filtered by cone_size / relationship type

**Why not Neo4j:** See [ADR-0002](adr/0002-graph-storage-strategy.md).

### 2.4 Data Retention

| Table | Retention | Rationale |
|---|---|---|
| `probe_measurements` | 90 days (configurable) | Training needs ~90 days; older data archived or dropped via TimescaleDB retention policy |
| `bgp_events` | 90 days | Same as measurements; BGP history beyond 90 days available from RouteViews archives if needed |
| `as_relationships` | Current only (overwritten on each CAIDA refresh) | Topology changes slowly; historical snapshots reconstructable from CAIDA archives |
| `incidents` | Indefinite | Low volume; historical incidents are valuable for trend analysis and model evaluation |
| `probes` | Current only | Live registry; historical probe data available from RIPE Atlas archives |

---

## 3. API Contract Style

### 3.1 REST API

- **Convention:** JSON:API-inspired, but not strictly compliant (pragmatic approach)
- **Versioning:** URL path prefix `/api/v1/`
- **Authentication:** JWT bearer tokens in `Authorization` header
- **Rate Limiting:** Redis-backed sliding window; 60 req/min default, 10 req/min burst
- **Pagination:** Cursor-based for time-series endpoints; offset-based for entity lists
- **Error Format:** Consistent `{ "error": { "code": "...", "message": "..." } }`
- **Caching:** `Cache-Control` headers on map/topology endpoints; Redis cache for hot data

### 3.2 Endpoint Categories

| Category | Pattern | Examples |
|---|---|---|
| **Map Data** | `GET /api/v1/map/*` | Probes, incident overlays, heatmap tiles |
| **AS Intelligence** | `GET /api/v1/as/{asn}/*` | Detail, predictions, neighbors |
| **Incidents** | `GET /api/v1/incidents/*` | List (paginated, filterable), detail + explanation |
| **Topology** | `GET /api/v1/topology` | AS graph subgraph for visualization |
| **Time Series** | `GET /api/v1/timeseries/{probe_id}` | Per-probe latency history |
| **Health** | `GET /health`, `GET /metrics` | System status, Prometheus metrics |

### 3.3 WebSocket Contract

A single WebSocket endpoint at `/ws/live` multiplexes message types:

```json
{
  "type": "incident" | "measurement" | "prediction" | "heartbeat",
  "timestamp": "2026-07-04T12:00:00Z",
  "data": { ... }
}
```

| Message Type | Trigger | Payload Summary |
|---|---|---|
| `incident` | New incident detected or updated | Incident ID, severity, type, affected ASNs |
| `measurement` | Aggregated probe anomaly update (every 30s) | Probe ID, anomaly score, RTT |
| `prediction` | New GNN prediction batch (every hour) | AS list with instability scores |
| `heartbeat` | Every 30 seconds | Server timestamp, connection count |

**Subscription model:** Clients can send a filter message on connect to subscribe
to specific ASNs, regions, or severity levels. Unfiltered connections receive all
messages (with rate limiting applied).

---

## 4. Component Responsibilities

### 4.1 Ingestion Layer

| Component | Responsibility | I/O |
|---|---|---|
| `ripe_atlas.py` | Poll public built-in measurements via REST API | → `probe_measurements`, `probes` |
| `ris_live.py` | Consume BGP updates via WebSocket stream | → `bgp_events` |
| `routeviews.py` | Download + parse MRT archives (BGPKIT) | → `bgp_events` |
| `caida.py` | Download + parse AS relationship dataset | → `as_relationships`, `as_metadata` |
| `cloudflare_radar.py` | Poll outage/traffic signals via REST API | → `incidents.metadata` (corroboration) |

### 4.2 ML Engine

| Component | Responsibility | I/O |
|---|---|---|
| `anomaly.py` | Statistical anomaly detection (Z-score, MAD) | `probe_measurements`, `bgp_events` → anomaly scores |
| `timeseries.py` | LSTM/Transformer latency forecasting | `probe_measurements` → predicted RTT |
| `gnn.py` | Temporal GNN instability prediction | `as_relationships` + features → per-AS instability score |
| `explainer.py` | Claude API bounded explanation calls | Structured incident JSON → natural-language explanation |

### 4.3 Backend API

| Component | Responsibility |
|---|---|
| `routes/health.py` | Health check with dependency status |
| `routes/map.py` | Map data endpoints (probes, incidents) |
| `routes/as_detail.py` | AS intelligence endpoints |
| `routes/incidents.py` | Incident CRUD + explanation retrieval |
| `routes/topology.py` | AS graph subgraph endpoint |
| `routes/timeseries.py` | Per-probe latency history |
| `websocket.py` | WebSocket manager for live updates |
| `schemas.py` | Pydantic request/response models |

### 4.4 Frontend

| Component | Responsibility |
|---|---|
| `map/` | deck.gl interactive world map with probe/incident layers |
| `graph/` | AS topology graph visualization (force-directed) |
| `timeline/` | Historical incident timeline with filters |
| `ui/` | Shared design system components |
| `hooks/` | `useWebSocket`, `useFetch`, `useMap` custom hooks |
| `lib/` | API client, TypeScript types, utilities |

---

## 5. Security Model

### 5.1 Authentication

- **JWT tokens** signed with HS256 (configurable to RS256 for production)
- Access tokens expire after 60 minutes (configurable)
- API keys for programmatic access (stored hashed in database)

### 5.2 Rate Limiting

- Redis-backed sliding window counter
- Default: 60 requests/minute per authenticated user
- Burst: 10 requests above limit before hard rejection
- Map tile endpoints: higher limit (120 req/min) due to multi-tile loads

### 5.3 Data Sensitivity

- All ingested data is **publicly available** from external sources
- No PII is collected or stored
- Incident explanations are generated from structured data, never from user input
- Claude API calls never receive user-submitted content

---

## 6. Failure Modes & Graceful Degradation

| Failure | Impact | Mitigation |
|---|---|---|
| RIS Live WebSocket disconnect | BGP event gap | Auto-reconnect with exponential backoff; gap filled from RouteViews on next cycle |
| RIPE Atlas API down | No new probe measurements | Serve cached data; statistical anomaly continues on existing data |
| PostgreSQL down | Full outage | Health check returns `unhealthy`; no graceful degradation for core storage |
| Redis down | No caching, no rate limiting | Fall through to database; accept slower responses |
| Claude API down / budget exhausted | No incident explanations | Serve structured incident data without explanation text |
| GNN model not yet trained | No instability predictions | Statistical anomaly detection provides baseline coverage |
| Cloudflare Radar down | No corroboration signal | Non-critical; incident detection works without it |
