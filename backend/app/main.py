"""
NetPulse Backend — FastAPI application entry point.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.config import get_settings
from app.dependencies import lifespan_dependencies, shutdown_dependencies
from app.observability.logging import setup_logging

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
        allow_origins=[
            "http://localhost:3000",  # Next.js dev server
            "https://*.vercel.app",   # Vercel deployments
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────────
    app.include_router(health_router)

    return app


# The app instance — used by `uvicorn app.main:app`
app = create_app()
