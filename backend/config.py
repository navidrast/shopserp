"""
ShopSerp configuration via pydantic-settings.

All settings can be overridden through environment variables or a .env file
located at the project root.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SHOPSERP_",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./shopserp.db"

    # ── Scraping ──────────────────────────────────────────────────────
    SCRAPE_INTERVAL_MINUTES: int = 360
    REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_SCRAPES: int = 3

    # ── Proxy ─────────────────────────────────────────────────────────
    PROXY_URL: str | None = None
    PROXY_ROTATION_ENABLED: bool = False

    # ── Geo / Locale ──────────────────────────────────────────────────
    DEFAULT_COUNTRIES: list[str] = Field(default_factory=lambda: ["US"])

    # ── Alerts ────────────────────────────────────────────────────────
    ALERT_WEBHOOK_URL: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────
    SECRET_KEY: str | None = None

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


settings = Settings()
