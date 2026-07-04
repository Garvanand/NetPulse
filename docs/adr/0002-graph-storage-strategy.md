# ADR-0002: Graph Storage Strategy — Postgres Adjacency over Neo4j

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** NetPulse architecture review

---

## Context

NetPulse models the internet as an **AS (Autonomous System) topology graph**
derived from the CAIDA AS Relationships dataset. This graph has:

- **~75,000 nodes** (ASes) — MVP subgraph: ~2,000–5,000 transit ASes
- **~300,000 edges** — AS-to-AS relationships (customer/peer/provider)
- **Update frequency:** Daily (CAIDA refreshes periodically; AS relationships
  change on a timescale of days to weeks)

The graph is consumed by three subsystems:
1. **ML Engine (GNN):** Needs the full adjacency matrix + node features as a
   PyTorch Geometric `Data` object. Loaded in bulk once per training/inference
   cycle (hourly).
2. **API (topology endpoint):** Returns filtered subgraphs for frontend
   visualization. Typical query: "give me AS X and its 2-hop neighbors."
3. **Feature engineering:** Join AS metadata (degree, cone size) with
   measurement features during snapshot construction.

## Decision

Store the AS topology as a **relational adjacency list** in PostgreSQL
(`as_relationships` table with `asn_a`, `asn_b`, `rel_type` columns), not in
a dedicated graph database like Neo4j.

## Consequences

### Positive

- **No additional infrastructure** — the graph lives in the same PostgreSQL
  instance as all other data. Zero additional operational burden.
- **Simple bulk loading** — CAIDA dataset is a flat file of `ASN_A|ASN_B|rel_type`
  triples. Direct `COPY` or upsert into a relational table is trivial.
- **SQL joins work** — enriching graph nodes with time-series features
  (probe measurements, BGP churn) is a standard SQL join, not a cross-database
  query.
- **GNN compatibility** — PyTorch Geometric expects edge lists as tensor pairs
  `(source[], target[])`. Converting a SQL result set to edge index tensors is
  a simple numpy operation; no graph database query language needed.
- **Adequate query performance** — with indexes on `asn_a` and `asn_b`, a
  2-hop neighborhood query on a 300K-edge graph completes in <10ms. The
  topology endpoint returns a filtered subgraph, not the full graph.

### Negative

- **No native graph traversal** — multi-hop path queries (e.g., "find all paths
  between AS X and AS Y") require recursive CTEs in SQL, which are less ergonomic
  than Cypher. However, NetPulse does not perform arbitrary path traversals;
  the GNN handles path-level reasoning.
- **No built-in graph algorithms** — algorithms like PageRank, community detection,
  or betweenness centrality are not available in SQL. Mitigated by computing these
  in Python (networkx or PyG) on the in-memory graph snapshot.
- **Large subgraph queries** — returning the full 75K-node graph via the API
  is expensive. Mitigated by always filtering (by cone_size threshold, region,
  or relationship type) and caching in Redis.

## Alternatives Considered

### Neo4j

- **Pro:** Native graph database with Cypher query language, built-in graph
  algorithms (GDS library), excellent visualization tools.
- **Con:**
  - **Additional infrastructure:** Neo4j is a separate JVM-based service that
    needs its own hosting, monitoring, and backup strategy. Unacceptable
    operational burden for a single-developer portfolio project.
  - **Data synchronization:** Graph features (BGP churn, latency) live in
    PostgreSQL. Keeping Neo4j nodes in sync with Postgres time-series data
    requires a synchronization pipeline — additional complexity and failure modes.
  - **GNN export:** PyTorch Geometric does not natively consume Neo4j graphs.
    Data would still need to be exported to edge lists. No advantage over SQL.
  - **Cost:** Neo4j Aura (managed) starts at $65/month for a small instance.
    The graph fits comfortably in Postgres on an existing instance at zero
    marginal cost.
- **Rejected:** The operational cost far outweighs the ergonomic benefits for
  NetPulse's query patterns.

### In-Memory Graph (networkx)

- **Pro:** Zero infrastructure; pure Python; rich algorithm library.
- **Con:** Not persistent. Must be rebuilt on every restart. ~75K nodes fits in
  memory (~50MB), but introduces a cold-start delay and no crash resilience.
  Also not queryable via API without custom serialization.
- **Rejected:** Persistence and API queryability require a backing store. Postgres
  fills this role; networkx can be used as a derived in-memory representation
  for algorithm computation.

### Dedicated Graph Column in Postgres (JSONB adjacency)

- **Pro:** Single column stores the full adjacency for each node.
- **Con:** Extremely expensive updates (rewrite full JSONB on edge change),
  poor query performance for graph traversals, no relationship-type filtering
  at query time.
- **Rejected:** Relational adjacency list is strictly better for this use case.

## Re-evaluation Trigger

If NetPulse grows to require:
- Interactive multi-hop path exploration in the UI (>3 hops)
- Built-in graph algorithm execution on the live topology (not pre-computed)
- A customer-facing graph query API

Then Neo4j should be reconsidered. The adjacency list schema is forward-compatible:
the migration path is a one-time ETL from `as_relationships` to Neo4j nodes/edges.
