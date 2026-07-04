"""
NetPulse Backend — Dependency injection and lifespan management.

Manages shared resources: database engine, async session factory, and Redis client.
"""

from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = structlog.get_logger()

# ── Module-level state (set during lifespan) ────────────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: Redis | None = None


# ── Lifespan helpers ────────────────────────────────────────────────


async def lifespan_dependencies(app: FastAPI) -> None:
    """Initialize shared resources on application startup."""
    global _engine, _session_factory, _redis

    settings = get_settings()

    # Database engine
    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("database_connected", url=settings.database_url.split("@")[-1])

    # Redis
    _redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    # Verify connectivity
    try:
        await _redis.ping()
        logger.info("redis_connected", url=settings.redis_url)
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        _redis = None

    # Store references on the app for access in routes
    app.state.db_engine = _engine
    app.state.db_session_factory = _session_factory
    app.state.redis = _redis


async def shutdown_dependencies(app: FastAPI) -> None:
    """Clean up shared resources on application shutdown."""
    global _engine, _session_factory, _redis

    if _redis is not None:
        await _redis.aclose()
        logger.info("redis_disconnected")

    if _engine is not None:
        await _engine.dispose()
        logger.info("database_disconnected")

    _engine = None
    _session_factory = None
    _redis = None


# ── FastAPI dependency functions ────────────────────────────────────


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.
    Usage in routes: `session: AsyncSession = Depends(get_db_session)`
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized — app lifespan may not have started")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis() -> Redis | None:
    """
    Return the Redis client (or None if unavailable).
    Usage in routes: `redis: Redis | None = Depends(get_redis)`
    """
    return _redis
