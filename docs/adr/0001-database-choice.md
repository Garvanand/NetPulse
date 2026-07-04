# ADR-0001: Database Choice — PostgreSQL + TimescaleDB

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** NetPulse architecture review

---

## Context

NetPulse ingests two categories of data with fundamentally different access patterns:

1. **Time-series measurement data** — Probe latency readings (~12K probes × every 5 min = ~3.5M rows/day) and BGP events (~1K events/sec during convergence bursts) that are almost exclusively appended and queried by time range.

2. **Entity/relational data** — AS topology graph (~75K nodes, ~300K edges), probe registry (~12K rows), and incidents (tens per day) that require standard CRUD operations, joins, and complex filtering.

The system runs on a **single instance** (no distributed cluster), must support
hypertable-style automatic partitioning for time-series, and needs to minimize
operational complexity for a solo developer.

## Decision

Use **PostgreSQL 16+ with the TimescaleDB extension** as the single database
for both time-series and relational data.

- Time-series tables (`probe_measurements`, `bgp_events`) are created as
  **TimescaleDB hypertables**, automatically partitioned by time.
- Relational tables (`probes`, `as_relationships`, `as_metadata`, `incidents`)
  remain standard PostgreSQL tables.
- All tables live in the same database instance.

## Consequences

### Positive

- **Single database to operate** — no need to run and synchronize two different
  database systems (e.g., Postgres + InfluxDB).
- **Time-series superpowers** — TimescaleDB provides automatic chunk management,
  retention policies (`drop_chunks`), continuous aggregates for pre-computed
  rollups, and compression for older data.
- **Full SQL** — complex analytical queries (joins between time-series and
  entity tables) work natively; no impedance mismatch.
- **Mature ecosystem** — excellent Python support via SQLAlchemy + asyncpg;
  Alembic migrations work (hypertable creation via raw SQL in migration).
- **Hosting options** — Timescale Cloud (managed), Railway Postgres (self-managed
  with extension), or any Postgres host that supports extensions.
- **Familiar operations** — standard pg_dump, pg_restore, VACUUM, EXPLAIN ANALYZE.

### Negative

- **Extension dependency** — TimescaleDB must be available on the hosting provider.
  Not all managed Postgres services support it (Vercel Postgres does not, but
  Timescale Cloud, Supabase, and Railway do).
- **Not a dedicated TSDB** — InfluxDB or QuestDB might offer marginally better
  write throughput for pure time-series workloads, but the difference is
  negligible at NetPulse's scale (~40 inserts/sec average).
- **Hypertable limitations** — Some PostgreSQL features (e.g., unique constraints
  not including the partitioning column) behave differently on hypertables.
  Mitigated by using composite primary keys `(time, id)`.

## Alternatives Considered

### InfluxDB

- **Pro:** Purpose-built TSDB with excellent write throughput and retention.
- **Con:** Requires a separate relational database for entity data. Two databases
  to operate, synchronize, and monitor. InfluxQL/Flux is less expressive than SQL.
  Overkill for our scale.
- **Rejected:** Operational complexity unacceptable for single-developer project.

### QuestDB

- **Pro:** Very fast SQL-compatible TSDB.
- **Con:** Less mature ecosystem than Postgres. No rich relational features
  (foreign keys, JSONB, array types). Would still need a second database.
- **Rejected:** Same dual-database problem as InfluxDB.

### Vanilla PostgreSQL (no TimescaleDB)

- **Pro:** Zero extension dependency; works on any Postgres host.
- **Con:** Manual table partitioning required for time-series performance.
  No built-in retention policies, continuous aggregates, or chunk compression.
  Significant DIY operational burden for time-range queries on large tables.
- **Rejected:** TimescaleDB's automatic chunking and retention are worth the
  extension dependency.

### ClickHouse

- **Pro:** Excellent analytical performance on columnar data.
- **Con:** Not designed for point queries or updates. No rich relational model.
  Would need a companion OLTP database.
- **Rejected:** Wrong tool for a mixed workload.
