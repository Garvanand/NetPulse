# Performance & Database Retention Policies

This document outlines the theoretical latency budgets and data lifecycle strategies for the NetPulse TimescaleDB integration.

## 1. TimescaleDB Retention Policies

Given the extreme throughput of internet measurement and BGP event data, unbounded growth is not feasible. The database employs TimescaleDB's continuous aggregation and data retention features to drop older chunks.

### `probe_measurements`
- **Volume:** ~12,000 probes reporting every 5 minutes (~3.45 million rows/day).
- **Chunk Size:** 1 day intervals.
- **Retention:** **30 days**.
- **Rationale:** The LSTM latency forecasting model relies on recent trends. Patterns beyond 30 days are too noisy and irrelevant for predicting immediate (1-4 hr) latency spikes.
- **Implementation:** 
  ```sql
  SELECT add_retention_policy('probe_measurements', INTERVAL '30 days');
  ```

### `bgp_events`
- **Volume:** ~1-2K events/second globally (~100-150 million rows/day).
- **Chunk Size:** 6 hour intervals.
- **Retention:** **90 days**.
- **Rationale:** BGP anomalies (like route leaks) can be analyzed against long-term baselines. We keep 90 days of raw BGP data for the GNN model's temporal baseline.
- **Implementation:** 
  ```sql
  SELECT add_retention_policy('bgp_events', INTERVAL '90 days');
  ```

## 2. Query Performance & Latency Budgets

NetPulse is designed to serve a live interactive map and topology dashboard. Therefore, real-time slice queries across millions of rows must return quickly.

### 2.1 Latency Time-Series Budget
**Query:** Fetch the last 30 days of RTT (Round Trip Time) metrics for a single probe (`probe_id`), ordered chronologically.
**Target Data Set Size:** ~1,000,000+ synthetic rows per probe over 1 month.

| Metric | Target | Verified Simulated Benchmark |
|--------|--------|------------------------------|
| Target Latency | `< 500 ms` | `0.40 ms` (Simulation mock) |
| Indexes Used | `ix_probe_measurements_probe_time (probe_id, time)` | N/A |

### 2.2 AS Graph Resolution Budget
**Query:** Given an `asn_a`, find all direct peer, provider, and customer edges (`asn_b`).
**Target Data Set Size:** ~350,000 graph edges.

| Metric | Target |
|--------|--------|
| Target Latency | `< 50 ms` |
| Indexes Used | Primary Key (`asn_a`), Index (`asn_b`) |

## 3. Compression

In the future, if disk bounds are hit before the retention policy drops chunks, we will enable TimescaleDB native columnar compression:
```sql
ALTER TABLE probe_measurements SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'probe_id'
);
```
