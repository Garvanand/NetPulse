# NetPulse

> **Predict internet weather before it storms.**

A predictive internet path intelligence platform that combines real-time BGP data, active network measurements, and graph neural networks to forecast internet instability before it impacts users.

## Architecture

```
Frontend (Next.js + TypeScript)  →  Backend API (FastAPI)  →  PostgreSQL + TimescaleDB
         ↕ WebSocket                      ↕                          ↕
    Live incident updates           ML Engine (GNN)           Time-series data
                                         ↕
                                   Data Ingestion
                              (RIPE Atlas, RIS Live,
                           RouteViews, CAIDA, CF Radar)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+ with [TimescaleDB](https://docs.timescale.com/install/latest/) extension
- Redis 7+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env

### Required Environment Variables
Ensure `.env` is populated before starting the server. `NETPULSE_` prefix is required.

| Variable | Description |
|---|---|
| `NETPULSE_DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `NETPULSE_JWT_SECRET_KEY` | 32-byte hex secret for JWT signing |
| `NETPULSE_CLAUDE_API_KEY` | Anthropic API Key (Required for explanations) |
| `NETPULSE_CORS_ORIGINS` | JSON list of allowed origins (e.g. `["http://localhost:3000"]`) |

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend runs at `http://localhost:3000` and the backend API at `http://localhost:8000`.

### API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

## Data Sources

| Source | Type | Refresh |
|---|---|---|
| [RIPE Atlas](https://atlas.ripe.net/) | Active measurements (ping/traceroute/DNS) | Every 5 min |
| [RIPE RIS Live](https://ris-live.ripe.net/) | Real-time BGP updates (WebSocket) | Continuous |
| [RouteViews](http://archive.routeviews.org/) | BGP RIB/update archives (MRT) | Every 15 min |
| [CAIDA AS Relationships](https://www.caida.org/catalog/datasets/as-relationships/) | AS topology graph | Daily |
| [Cloudflare Radar](https://radar.cloudflare.com/) | Traffic/outage corroboration | Every 15 min |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Environment configuration
│   │   ├── dependencies.py      # DI container (DB, Redis)
│   │   ├── api/                 # REST + WebSocket routes
│   │   ├── ingestion/           # Data source connectors
│   │   ├── ml/                  # ML engine (anomaly, GNN, explainer)
│   │   ├── storage/             # Models, repositories, migrations
│   │   └── observability/       # Logging, metrics, health
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/                    # Next.js + TypeScript + TailwindCSS
├── memory.md                    # Architecture decisions & data source status
├── plan.md                      # Implementation plan (9 phases)
├── FEASIBILITY.md               # Risk register & scope-down path
└── README.md
```

## Attribution

This project uses the following datasets:

- **CAIDA AS Relationships Dataset** — "The CAIDA AS Relationships Dataset, https://www.caida.org/catalog/datasets/as-relationships/"
- **RIPE Atlas** — RIPE NCC, https://atlas.ripe.net/
- **RIPE RIS** — RIPE NCC, https://ris.ripe.net/
- **RouteViews** — University of Oregon, http://www.routeviews.org/
- **Cloudflare Radar** — Cloudflare, Inc. (CC BY-NC 4.0), https://radar.cloudflare.com/

## License

MIT
