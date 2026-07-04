# ML Feature Engineering

This document details the feature vectors engineered from the raw NetPulse database for the Temporal GNN and LSTM forecasting models.

## 1. Node Features (AS Level)

Each Autonomous System (AS) in the graph is represented by a feature vector `x_i(t)` at time step `t`. We use a 6-hour sliding window.

| Index | Feature Name | Description | Source Field | Rationale |
|---|---|---|---|---|
| 0 | `mean_rtt_ms` | Average RTT of all probes residing in this AS during the window. | `probe_measurements.rtt_ms` | Elevated latency indicates internal congestion or routing sub-optimality. |
| 1 | `packet_loss_rate` | Ratio of failed pings to total pings originating from this AS. | `probe_measurements.packet_loss` | Direct indicator of severe reachability issues. |
| 2 | `bgp_announcements` | Count of BGP announcements originating from this AS. | `bgp_events.event_type == 'announce'` | High churn suggests route flapping or instability. |
| 3 | `bgp_withdrawals` | Count of BGP withdrawals originating from this AS. | `bgp_events.event_type == 'withdraw'` | Sudden spikes indicate route leaks or outages. |
| 4 | `cone_size_log` | `log10(cone_size + 1)` from CAIDA metadata. | `as_metadata.cone_size` | Tier-1 providers have different baseline behaviors than edge ISPs. |

## 2. Edge Features (AS Relationships)

Edges are derived from the CAIDA dataset and represented as an adjacency matrix or edge index.

| Index | Feature Name | Description | Source Field |
|---|---|---|---|
| 0 | `is_provider` | 1 if AS_A provides transit to AS_B, else 0 | `as_relationships.rel_type == 'provider'` |
| 1 | `is_peer` | 1 if AS_A peers with AS_B, else 0 | `as_relationships.rel_type == 'peer'` |
| 2 | `is_customer` | 1 if AS_A is a customer of AS_B, else 0 | `as_relationships.rel_type == 'customer'` |

## 3. Univariate Time Series (Probe Level)

For the localized latency forecasting model (LSTM), we extract a pure time-series sequence `y(t)` for each probe.

| Feature Name | Description | Source Field |
|---|---|---|
| `rtt_ms` | The specific latency reading at time `t`. | `probe_measurements.rtt_ms` |

## Missing Data Imputation
- Nodes with no probe measurements in the 6-hour window inherit a rolling average of their last known state, or default to median global latency if completely cold.
- BGP event counts default to `0` if absent.
