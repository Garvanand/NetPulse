# NetPulse Testing Strategy

NetPulse employs a **Test Pyramid** strategy designed for maximum coverage of critical ML analytics pipelines while respecting the practical limitations of testing complex visual WebGL components in CI.

## 1. Unit & Integration Testing (The Foundation)

### Backend (FastAPI + TimescaleDB)
- **Target Coverage**: `> 80%` on core business logic (Ingestion parsing, ML Incident Engine, Repositories).
- **Execution**: `pytest --cov=app tests/`
- **What is covered**:
  - **Repositories**: Standard CRUD and complex time-series queries. Mocked via `unittest.mock.AsyncMock`.
  - **ML Features**: Deterministic tests ensuring specific BGP signatures and Latency arrays always yield the exact expected floating-point Tensors.
  - **Incident Engine**: Boundary testing (True Positive, False Positive) for statistical anomaly and GNN thresholds.
  - **API Contracts**: Every router endpoint enforces schema validation.

### Frontend (Next.js)
- **Execution**: `vitest run`
- **What is covered**:
  - **Incident Utilities**: Pure mathematical functions for sorting arrays of incidents by severity and timestamp.
- **What is excluded**:
  - Components with heavy Canvas/WebGL dependencies (`react-map-gl`, `react-force-graph-2d`) intentionally bypass JSDOM to avoid segmentation faults in CI.

## 2. End-to-End Testing (The Peak)

We use **Playwright** for full-stack integration testing, driving an actual headless browser against our Next.js frontend.

- **Execution**: `npm run test:e2e` (Ensure backend is running locally on `:8000` and frontend on `:3000`).
- **Core Flow Monitored**:
  1. The user navigates through the main layouts (Overview -> Live Map -> Topology -> Incidents).
  2. The E2E script verifies the existence of the complex WebGL/Canvas wrapper divs (`.maplibregl-canvas-container`).
  3. The script simulates clicking a generated Incident and expects the Anthropic LLM Explanation Card and the Recharts Telemetry Line Chart to render within the timeout windows.

## 3. Explicit Exclusions & Known Limitations

To maintain a robust CI pipeline, the following items are intentionally excluded from automated testing (and instead require Manual QA or are monitored via observability platforms):

1. **Live Third-Party API Calls**: The Anthropic API and RIPE Atlas API are rigidly mocked in our Pytest suite. We do NOT spend API credits on CI runs.
2. **WebGL Rendering Correctness**: Playwright cannot natively assert if a WebGL force-directed graph "looks" physically correct or if a Framer Motion pulsating animation is centered. These require manual visual spot checks (see the Manual QA Checklist in Prompt 10).
3. **Flaky Tests**: Any tests reliant on `asyncio.sleep()` or non-deterministic time-windows are marked with `@pytest.mark.xfail` or rigidly mocked with frozen time via `freezegun`.
