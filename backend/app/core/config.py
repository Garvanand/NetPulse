"""
NetPulse Backend — Predictive internet path intelligence platform.

Configuration management via pydantic-settings.
All settings are loaded from environment variables (or .env file).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NETPULSE_",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "NetPulse"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Server ───────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1  # Single instance — no multi-worker needed

    # ── Database (PostgreSQL + TimescaleDB) ──────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://netpulse:netpulse@localhost:5432/netpulse",
        description="Async PostgreSQL connection string",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and rate limiting",
    )
    redis_cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")

    # ── JWT Auth ─────────────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"),
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ── RIPE Atlas API ───────────────────────────────────────────────
    ripe_atlas_api_key: str = Field(default="", description="RIPE Atlas API key")
    ripe_atlas_base_url: str = "https://atlas.ripe.net/api/v2"
    ripe_atlas_poll_interval_seconds: int = 300  # 5 minutes

    # ── RIPE RIS Live ────────────────────────────────────────────────
    ris_live_ws_url: str = "wss://ris-live.ripe.net/v1/ws/?client=netpulse"

    # ── RouteViews ───────────────────────────────────────────────────
    routeviews_archive_url: str = "http://archive.routeviews.org"
    routeviews_poll_interval_seconds: int = 900  # 15 minutes

    # ── CAIDA ────────────────────────────────────────────────────────
    caida_dataset_url: str = (
        "https://publicdata.caida.org/datasets/as-relationships/serial-2/"
    )
    caida_refresh_interval_seconds: int = 86400  # Daily

    # ── Cloudflare Radar ─────────────────────────────────────────────
    cloudflare_radar_api_token: str = Field(
        default="", description="Cloudflare Radar API token"
    )
    cloudflare_radar_base_url: str = "https://api.cloudflare.com/client/v4/radar"
    cloudflare_radar_poll_interval_seconds: int = 900  # 15 minutes

    # ── Claude API (Explanation Layer) ───────────────────────────────
    claude_api_key: SecretStr = Field(
        default=SecretStr(""), description="Anthropic Claude API key"
    )
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_calls_per_hour: int = 10
    claude_cache_ttl_seconds: int = 86400  # 24 hours

    # ── Rate Limiting ────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql+asyncpg://", "postgresql://", "sqlite")):
            raise ValueError("database_url must be a PostgreSQL or SQLite connection string")
        return v

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
