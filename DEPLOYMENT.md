# NetPulse Deployment Guide

This guide details the exact steps required to provision and deploy the NetPulse platform into a production environment. 

Our target architecture explicitly avoids Docker and Kubernetes in favor of single-instance PaaS solutions (see [ADR-0005](docs/adr/0005-deployment-strategy-no-docker.md)). 

---

## 1. Database Provisioning (Timescale Cloud)

NetPulse requires PostgreSQL 16+ with the TimescaleDB extension. Self-hosting this on the same VPS as the API is strictly discouraged due to the massive ingestion volume.

1. **Create Account**: Go to [Timescale Cloud](https://console.timescale.com/) and create a new project.
2. **Provision Service**: Create a new Time-Series database (Compute: 1 CPU, 4GB RAM is sufficient for the MVP).
3. **Capture Credentials**: Copy the `Service URI` (looks like `postgres://tsdbadmin:password@host:port/defaultdb?sslmode=require`).
4. **Estimated Cost**: ~$30/month for the Developer tier.

---

## 2. Backend Provisioning (Railway)

We use [Railway](https://railway.app/) for the backend API because of its native Nixpacks builder, which eliminates the need to write and maintain complex Python Dockerfiles.

1. **Connect GitHub**: Log into Railway and create a "New Project" > "Deploy from GitHub repo".
2. **Select Repository**: Choose your NetPulse repository.
3. **Configure Root Directory**: In the service settings, set the Root Directory to `/backend`.
4. **Provision Redis**: In the same Railway Project, click "New" > "Database" > "Add Redis".
5. **Inject Secrets**: Go to the API service "Variables" tab and add the following:
   - `NETPULSE_DATABASE_URL` = (Your Timescale Cloud URI)
   - `NETPULSE_REDIS_URL` = (The internal `REDIS_URL` provided by Railway)
   - `NETPULSE_JWT_SECRET_KEY` = (Generate via `openssl rand -hex 32`)
   - `NETPULSE_CLAUDE_API_KEY` = (Your Anthropic API key)
   - `NETPULSE_CORS_ORIGINS` = `["https://your-frontend-domain.vercel.app"]`
6. **Deploy**: The `railway.toml` file automatically triggers `alembic upgrade head` and starts the Uvicorn server.
7. **Generate Domain**: Go to "Settings" > "Networking" and click "Generate Domain" to expose the API publicly.
8. **Estimated Cost**: ~$5/month (Hobby Plan).

---

## 3. Scheduled Jobs (Railway Cron)

NetPulse requires background tasks to poll CAIDA, RouteViews, and RIPE Atlas. We use Railway Cron instead of in-process orchestrators.

1. In the Railway API service settings, go to the "Cron" tab.
2. Add a new Cron Job:
   - **Command**: `python scripts/run_ingestion.py`
   - **Schedule**: `0 * * * *` (Every hour)
3. This job will execute natively within the exact same environment and utilize the same secrets as the running API.

---

## 4. Frontend Provisioning (Vercel)

The Next.js frontend is deployed to Vercel for automatic edge-caching and CDN distribution.

1. **Connect GitHub**: Log into [Vercel](https://vercel.com/) and click "Add New Project".
2. **Select Repository**: Choose your NetPulse repository.
3. **Configure Root Directory**: Set the Root Directory to `frontend`. Vercel will automatically detect the Next.js framework.
4. **Inject Secrets**: Add the following Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-railway-api-domain.up.railway.app`
5. **Deploy**: Click Deploy. The `vercel.json` file will automatically enforce secure HTTP headers.
6. **Estimated Cost**: Free (Hobby Tier).

---

## Maintenance & Redeployment

- **Continuous Deployment**: Both Vercel and Railway are configured to auto-deploy whenever you push code to the `main` branch.
- **Rollbacks**: If a deployment fails, both platforms allow one-click rollbacks to the previous successful build from their respective dashboards.
- **Migrations**: Database migrations (`alembic upgrade head`) are safely executed on every backend startup natively via the `startCommand` in `backend/railway.toml`.
