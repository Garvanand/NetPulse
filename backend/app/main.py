"""
NetPulse Backend — FastAPI application entry point.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
from fastapi import Request

from app.api.routes.health import router as health_router
from app.api.measurements.router import router as measurements_router
from app.api.bgp.router import router as bgp_router
from app.api.topology.router import router as topology_router
from app.api.incidents.router import router as incidents_router
from app.api.predictions.router import router as predictions_router
from app.api.ws.router import router as ws_router

from app.core.config import get_settings
from app.core.dependencies import lifespan_dependencies, shutdown_dependencies
from app.core.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "starting_netpulse",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database and Redis connections
    await lifespan_dependencies(app)

    logger.info("netpulse_started", host=settings.host, port=settings.port)
    yield

    # Cleanup
    logger.info("shutting_down_netpulse")
    await shutdown_dependencies(app)
    logger.info("netpulse_stopped")


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Predictive internet path intelligence platform"
            " — predict internet weather before it storms."
        ),
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    # ── Middleware ───────────────────────────────────────────────
    @app.middleware("http")
    async def structlog_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_host=request.client.host if request.client else None,
            method=request.method,
            path=request.url.path,
        )
        
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            logger.info("request_completed", status_code=response.status_code, latency_ms=process_time*1000)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.error("request_failed", error=str(e), latency_ms=process_time*1000)
            raise

    # ── Routes ───────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(measurements_router)
    app.include_router(bgp_router)
    app.include_router(topology_router)
    app.include_router(incidents_router)
    app.include_router(predictions_router)
    app.include_router(ws_router)

    return app


# The app instance — used by `uvicorn app.main:app`
app = create_app()
