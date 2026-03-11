"""
ShopSerp configuration via pydantic-settings.

All settings can be overridden through environment variables or a .env file
located at the project root.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
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

    # ── Search API (optional, bypasses direct scraping) ───────────────
    # Set one of these for reliable results without a proxy:
    #   SERPER_API_KEY from https://serper.dev (2500 free searches)
    #   SERPAPI_KEY from https://serpapi.com
    SERPER_API_KEY: str | None = None
    SERPAPI_KEY: str | None = None

    # ── Geo / Locale ──────────────────────────────────────────────────
    DEFAULT_COUNTRIES: list[str] = Field(default_factory=lambda: ["US"])

    # ── Alerts ────────────────────────────────────────────────────────
    ALERT_WEBHOOK_URL: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────
    SECRET_KEY: str | None = None

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @field_validator("DEFAULT_COUNTRIES", mode="before")
    @classmethod
    def parse_countries(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v  # type: ignore[return-value]

    @field_validator("PROXY_URL", "ALERT_WEBHOOK_URL", "SECRET_KEY",
                     "SERPER_API_KEY", "SERPAPI_KEY", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


settings = Settings()
