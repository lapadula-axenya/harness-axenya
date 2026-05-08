"""Application settings, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://xenia:xenia@localhost:5432/xenia"
    database_url_sync: str = "postgresql+psycopg://xenia:xenia@localhost:5432/xenia"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "dev-only-not-for-prod-change-me"
    jwt_algorithm: str = "HS256"

    # LLM
    anthropic_api_key: str = ""
    omnirouter_api_key: str = ""
    omnirouter_base_url: str = ""

    # Agent registry
    agents_dir: Path = Path("agents")

    # Service
    service_name: str = "xenia-api"
    log_level: str = "INFO"
    env: str = "dev"

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""

    # Webhook secrets are pulled dynamically by env-var name (`webhook_secret_env` field
    # on the agent definition). We expose a helper rather than hard-coding fields.
    webhook_timestamp_skew_seconds: int = Field(default=300, ge=1)

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
