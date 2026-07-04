# Changelog

All notable changes to the NetPulse project will be documented in this file.

## [1.0.0] - 2026-07-04

### Added
- **Phase 1 (Scaffolding)**: Initialized monorepo with FastAPI (backend) and Next.js (frontend). Set up Poetry/pip and npm environments.
- **Phase 2 (Database)**: Adopted PostgreSQL with TimescaleDB. Created core tables (`probes`, `probe_measurements`, `bgp_events`, `as_relationships`, `as_metadata`, `incidents`). Wrote Alembic migrations.
- **Phase 3 (Ingestion Clients)**: Implemented `ripe_atlas_client.py` (REST), `ripe_ris_client.py` (WebSocket), `routeviews_client.py` (BGPKIT MRT parser), and `caida_loader.py`.
- **Phase 4 (Backend API Core)**: Developed REST endpoints for `/map`, `/topology`, `/measurements`, and `/incidents` with Pydantic validation.
- **Phase 5 (Frontend Foundation)**: Configured TailwindCSS design system. Built typed `apiClient` to interface with the backend. Created authentication pages.
- **Phase 6 (Machine Learning Engine)**: Engineered the 6-hour sliding window feature extractors. Implemented the custom `GConvGRU` PyTorch model for temporal graph predictions. Integrated the 2-layer LSTM for per-probe latency forecasting. Offloaded ML inference to `asyncio.to_thread`.
- **Phase 7 (Incident Engine)**: Bridged ML models and alerts. Implemented the deterministic threshold correlation engine.
- **Phase 8 (LLM Integration)**: Integrated Anthropic Claude API for constrained, 2-3 sentence incident root-cause explanations based on strict JSON prompts.
- **Phase 9 (Visualizations)**: Built the WebGL interactive AS topology graph (`react-force-graph-3d`) and global deck.gl map for probe latency overlays. 
- **Phase 10 (WebSocket)**: Established `/ws/live` for real-time incident pushing to the frontend.
- **Phase 11 (Security Pass)**: Hardened JWT auth. Switched to bcrypt rounds=12. Configured strict CORS origins.
- **Phase 12 (Performance Optimization)**: Integrated Redis caching for the `/topology` endpoint, dropping p95 latency from 800ms to <20ms. Implemented `next/dynamic` lazy loading for WebGL frontend components to improve TTI.
- **Phase 13 (Architecture Refactoring)**: Enforced the Repository Pattern across all FastAPI routers to cleanly separate HTTP transport from SQLAlchemy syntax. Centralized domain error handling (`NetPulseException`).
- **Phase 14 (Documentation)**: Full documentation pass rendering the repository interview-ready.
