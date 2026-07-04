# ADR-0005: Deployment Strategy — No Docker, Single-Service

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** NetPulse architecture review

---

## Context

NetPulse is a **portfolio-grade project** built and operated by a single
developer. The production deployment target is:

- **Frontend:** Vercel (static/SSR Next.js, edge-cached)
- **Backend:** Railway or Fly.io (single Python process)
- **Database:** Managed PostgreSQL + TimescaleDB (Timescale Cloud or Railway)
- **Cache:** Managed Redis (Upstash or Railway)

The backend is a single FastAPI application that embeds all functionality:
REST API, WebSocket server, ML inference, data ingestion (APScheduler), and
structured logging.

The question: should we containerize with Docker and/or orchestrate with
Kubernetes?

## Decision

**No Docker. No Kubernetes. No container orchestration.**

The backend is deployed as a **single Python process** directly on Railway or
Fly.io using their native buildpack/nixpack deployment (which internally
containerizes but abstracts it away from the developer).

The frontend is deployed to **Vercel** using its native Next.js integration.

## Consequences

### Positive

- **Zero container ops** — no Dockerfile to maintain, no image registry to
  manage, no multi-stage build optimization, no container security scanning.
  Railway and Fly.io detect Python projects and deploy them automatically
  from `pyproject.toml` or `requirements.txt`.
- **Simpler CI/CD** — push to main branch → automatic deployment. No Docker
  build step in the pipeline. Railway/Fly.io handle the build.
- **No orchestration overhead** — no Kubernetes manifests, Helm charts,
  pod scaling, service meshes, ingress controllers, or container networking.
  These are production-grade tools for production-grade teams; they add
  significant cognitive load for a single developer.
- **Single process model** — the backend is one Python process running
  uvicorn with APScheduler. Process management is handled by the platform
  (Railway/Fly.io auto-restarts on crash). No need to coordinate multiple
  containers (API + worker + scheduler).
- **Cost-efficient** — Railway Hobby plan ($5/mo) or Fly.io free tier
  provides sufficient compute for a single-instance deployment. No
  per-container overhead.
- **Development parity** — `uvicorn app.main:app --reload` in development
  is identical to the production command. No Docker Compose needed for
  local dev.
- **Faster iteration** — deploying a code change takes ~30 seconds
  (git push → platform builds → live). Docker image builds add 2–5 minutes.

### Negative

- **No local environment reproducibility** — without Docker, contributors
  (if any) must install Python, PostgreSQL, TimescaleDB, and Redis manually.
  Mitigated by:
  - Clear setup instructions in `README.md`
  - `.env.example` documenting all configuration
  - The project is single-developer; reproducibility for others is a
    nice-to-have, not a requirement
- **No multi-service compose** — if the architecture ever grows to multiple
  services (e.g., a separate ML training worker), Docker Compose would be
  valuable. Mitigated by the explicit non-goal of microservice sprawl.
- **Platform lock-in** — reliance on Railway/Fly.io buildpack behavior.
  However, the application is a standard Python ASGI app; it runs anywhere
  Python runs. Migrating to Docker later is a ~30-minute task (write a
  Dockerfile).
- **No GPU in production** — Railway and Fly.io don't offer GPU instances.
  GNN inference runs on CPU (acceptable for a 2K-node subgraph). Training
  is done offline on Colab/Lambda.

## Alternatives Considered

### Docker + Docker Compose (local), Docker deployment (prod)

- **Pro:** Reproducible environments; easy onboarding; standard deployment
  artifact; can include PostgreSQL + Redis in compose for local dev.
- **Con:**
  - **Maintenance burden:** Dockerfile, .dockerignore, multi-stage build,
    dependency caching, image size optimization. These are non-trivial
    for a Python project with C extensions (asyncpg, uvloop).
  - **Slower iteration:** Docker image build adds 2–5 minutes to each
    deployment cycle. Platform native deploys are faster.
  - **Complexity budget:** For a single developer, every piece of
    infrastructure is a maintenance liability. Docker is valuable for
    teams; it's overhead for a solo project.
- **Rejected:** The operational burden outweighs the benefits for a
  single-developer portfolio project.

### Kubernetes (EKS/GKE/k3s)

- **Pro:** Industry-standard orchestration; horizontal scaling; service
  mesh; health checks; rolling deployments.
- **Con:** Massively over-engineered for a single-process application.
  Kubernetes introduces:
  - Cluster management (or managed cluster cost: $75+/mo for EKS)
  - Manifests, Helm charts, ConfigMaps, Secrets
  - Ingress controller configuration
  - Pod resource limits and scheduling
  - Persistent volume claims for database
  - Monitoring stack (Prometheus Operator, Grafana)
  - At least 10 hours of setup before writing any application code
- **Rejected:** Wildly disproportionate to the deployment needs of a
  single-instance Python API.

### Serverless (AWS Lambda / Vercel Functions)

- **Pro:** Zero server management; auto-scaling; pay-per-invocation.
- **Con:**
  - **Cold starts:** FastAPI + SQLAlchemy + PyTorch models = 10+ second
    cold starts. Unacceptable for a real-time API.
  - **No long-lived connections:** WebSocket endpoints and the RIS Live
    WebSocket consumer require persistent connections. Serverless
    functions time out.
  - **No background tasks:** APScheduler jobs and the RIS Live consumer
    need a persistent process. Serverless has no equivalent without
    additional services (SQS, EventBridge, etc.).
  - **ML inference:** Loading a PyTorch model per invocation is absurd.
  - **Cost at scale:** Per-invocation pricing with always-on ingestion
    jobs would be more expensive than a single instance.
- **Rejected:** Fundamentally incompatible with long-lived connections,
  background tasks, and in-process ML inference.

## Migration Path

If NetPulse grows beyond a single-developer project and requires:
- Multi-instance deployment (horizontal scaling)
- Separate worker processes (ML training, heavy ingestion)
- Team onboarding with reproducible environments

Then adding Docker is a straightforward step:

```dockerfile
# Estimated 30-minute task
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This ADR does not reject Docker permanently; it rejects it **now** as
premature complexity.
