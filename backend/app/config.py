"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. In Docker these come from the container environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str
    database_url: str
    test_database_url: str
    session_ttl_days: int = 30
    login_max_attempts: int = 5
    login_window_minutes: int = 15
    # A write-off larger than this is worth a second look first. It is never
    # refused, only questioned, so this is a nudge rather than a limit.
    balance_check_warning_paise: int = Field(default=1_00_000, ge=0)
    # The daily interest job. Off in tests, so a suite never gains a second writer.
    scheduler_enabled: bool = True
    admin_email: str | None = None
    admin_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
