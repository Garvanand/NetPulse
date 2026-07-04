# Known Limitations

This document serves as an honest register of the technical debt, architectural constraints, and Machine Learning limitations present in the NetPulse platform as of Phase 14.

## 1. Machine Learning Limitations

As evaluated in `docs/ML_EVALUATION.md`, the predictive models significantly outperform statistical baselines but suffer from the following constraints:

### Temporal GNN (GConvGRU)
- **Static Edges Between Cycles**: The PyTorch model operates on a graph snapshot where the edges (AS Relationships) are presumed static for the 24-hour cycle. In reality, BGP peering relationships can break and form dynamically. If a major Tier-1 peering link drops, the GNN will not "know" about the structural change until the next daily CAIDA ingestion, potentially causing a false negative in its prediction cascade.
- **CPU Inference Bottleneck**: While we offload inference to `asyncio.to_thread` to prevent blocking the FastAPI event loop, the tensor operations still run on the CPU. Under massive load (e.g., expanding the AS graph from 2,000 to 70,000 nodes), inference time may exceed the 60-second acceptable threshold unless a dedicated GPU inference server is deployed.

### LSTM Forecaster
- **Cold-Start Problem**: The per-probe latency forecaster relies heavily on learning diurnal rhythms. When a new RIPE Atlas probe comes online, the model has no historical embedding for its topological location. It will default to predicting the global median latency until at least 48 hours of time-series data is ingested.

## 2. Ingestion & Architecture Limitations

### BGP MRT Parsing Delay
RouteViews MRT archives are heavily relied upon to fill gaps in the live RIS stream. However, these archives are published at 15-minute intervals. If the RIS Live WebSocket connection drops, there will be a mandatory 15-minute "blind spot" in the BGP churn metrics before the batch downloader can catch up.

### Single-Instance Scalability
The current deployment architecture (ADR-0005) explicitly avoids Kubernetes and microservice sprawl in favor of a monolithic FastAPI process. While simple to deploy, this means the WebSocket broadcaster (`/ws/live`) cannot horizontally scale across multiple instances without introducing a Pub/Sub backplane (e.g., Redis PubSub) to synchronize state between the servers.

### Frontend WebGL Limits
The Next.js frontend utilizes `deck.gl` and `react-force-graph-3d`. While lazy-loaded and highly optimized, rendering over 15,000 interactive AS nodes simultaneously in the browser will cause frame-rate drops on lower-end devices. We currently mitigate this by clustering nodes and pruning the topology graph to core networks only.
