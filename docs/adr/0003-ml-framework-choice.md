# ADR-0003: ML Framework Choice — PyTorch Geometric Temporal

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** NetPulse architecture review

---

## Context

NetPulse's core ML task is **predicting per-AS internet instability** on a
dynamic graph that evolves over time. This requires a model that can:

1. Operate on **graph-structured data** (AS topology with ~2K–75K nodes and
   typed edges: customer/peer/provider).
2. Capture **temporal dynamics** — the graph's node features (latency, BGP churn,
   anomaly scores) change at every time step, and the graph structure itself
   evolves slowly.
3. Produce **per-node predictions** (instability probability for each AS) rather
   than a single graph-level classification.
4. Be trainable on a **single GPU** (offline training on Colab/Lambda) and
   produce **CPU-friendly inference** for the deployed service.

Additionally, the project has a secondary ML task: **per-probe latency
forecasting** using an LSTM or lightweight Transformer on univariate time series.

## Decision

Use **PyTorch Geometric Temporal (PyG Temporal)** as the primary framework for
the temporal GNN, with **plain PyTorch** for the time-series LSTM/Transformer
head and statistical anomaly scorer.

Specifically:
- **GNN architecture:** Recurrent Graph Convolutional Network (RGCN with GRU
  recurrence) implemented via PyG Temporal's `DCRNN` or `GConvGRU` layers.
- **Time-series head:** 2-layer LSTM or single-layer Transformer encoder in
  plain PyTorch (no additional framework needed).
- **Anomaly scorer:** Pure statistical (numpy/scipy) — Z-score, Median Absolute
  Deviation, rolling window comparisons. No ML framework needed.

## Consequences

### Positive

- **Purpose-built for the task** — PyG Temporal provides pre-implemented temporal
  graph neural network architectures (A3TGCN, DCRNN, GConvGRU, EvolveGCN) that
  are designed exactly for spatiotemporal prediction on evolving graphs.
- **Temporal Signal Iterators** — the library's `DynamicGraphTemporalSignal` and
  `StaticGraphTemporalSignal` classes handle the conversion of graph snapshot
  sequences into training-ready batches with minimal boilerplate.
- **Built on PyTorch Geometric (PyG)** — inherits the full PyG ecosystem for
  graph operations: neighbor sampling, subgraph batching, GPU-accelerated sparse
  message passing. Essential for scaling to the 2K–5K node MVP subgraph.
- **Python-native** — integrates cleanly with the FastAPI backend. Model training
  produces standard `.pt` checkpoints loadable for CPU inference.
- **Active research community** — strong academic usage for network traffic
  prediction, internet topology modeling, and similar domains. Well-documented
  examples exist.
- **Flexible scaling** — start with a simple `GConvGRU` (few hundred lines of
  code), upgrade to `A3TGCN` (attention-based) if accuracy demands it. The
  `StaticGraphTemporalSignal` abstraction makes swapping architectures trivial.

### Negative

- **Learning curve** — PyG Temporal adds a layer of abstraction on top of PyG,
  which itself extends PyTorch. Three levels of framework to understand.
  Mitigated by the excellent documentation and tutorials.
- **Dependency weight** — PyTorch + PyG + PyG Temporal is a heavy dependency
  chain (~2GB installed). Mitigated by making ML dependencies optional
  (`[ml]` extra in pyproject.toml) and training offline.
- **CUDA version coupling** — PyG requires specific CUDA toolkit versions.
  Mitigated by training in a controlled environment (Colab, which provides
  pre-configured CUDA) and running inference on CPU.
- **Snapshot alignment** — the library expects pre-aligned graph snapshots.
  The feature engineering pipeline must handle the time-window alignment
  between CAIDA topology refreshes and streaming measurement data.

## Alternatives Considered

### Custom GNN Training Loop (raw PyTorch + PyG)

- **Pro:** Full control over the training loop; no PyG Temporal abstraction
  to learn; can implement novel temporal mechanisms.
- **Con:** Requires implementing temporal signal handling, snapshot batching,
  and recurrent graph convolution from scratch. Estimated 500–1000 lines of
  boilerplate that PyG Temporal provides out-of-the-box. Higher bug risk.
- **Rejected:** The engineering cost of reimplementing standard temporal GNN
  patterns is not justified for a portfolio project. PyG Temporal's
  abstractions match our use case exactly.

### TensorFlow + Spektral

- **Pro:** TensorFlow ecosystem; Spektral is a well-maintained GNN library.
- **Con:** Spektral has limited temporal graph support — no equivalent of PyG
  Temporal's `TemporalSignal` iterators. Would require building temporal
  handling manually. TensorFlow's graph mode adds debugging complexity.
  FastAPI ecosystem has stronger PyTorch integration (most ML research uses
  PyTorch).
- **Rejected:** Weaker temporal graph support and ecosystem fit.

### DGL (Deep Graph Library)

- **Pro:** Supports both PyTorch and TensorFlow backends; strong industry
  adoption (Amazon, etc.); good performance on large graphs.
- **Con:** DGL's temporal graph support is less mature than PyG Temporal's.
  No equivalent of `DynamicGraphTemporalSignal`. Would require more
  custom code for the snapshot-based temporal workflow. Slightly smaller
  research community for spatiotemporal prediction tasks.
- **Rejected:** PyG Temporal's temporal abstractions are more aligned with
  our discrete-snapshot approach.

### Classical ML (XGBoost / Random Forest on engineered features)

- **Pro:** No graph neural network needed; fast training; interpretable;
  CPU-only.
- **Con:** Cannot capture graph structure — each AS would be treated
  independently, losing the critical information about how instability
  propagates through the AS topology via customer/peer/provider
  relationships. This propagation is the core insight NetPulse aims to
  exploit.
- **Rejected:** Ignoring graph structure defeats the purpose of the
  predictive model.

## Implementation Notes

- **Training environment:** Google Colab (free T4 GPU) or Lambda Cloud
  ($0.50/hr GPU). Training runs offline; model checkpoints uploaded to
  the backend.
- **Inference:** CPU-only on the deployed Railway/Fly.io instance. A
  2K-node subgraph with 6–8 node features processes in <100ms on CPU.
- **Model versioning:** Checkpoints stored with timestamp; API reports
  active model version in `/health` response.
