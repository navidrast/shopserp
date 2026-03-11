"""
ShopSerp configuration via pydantic-settings.

All settings can be overridden through environment variables or a .env file
located at the project root.
"""

from __future__ import annotations

from pydantic import field_validator
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
    DEFAULT_COUNTRIES: str = "US"

    # ── Alerts ────────────────────────────────────────────────────────
    ALERT_WEBHOOK_URL: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────
    SECRET_KEY: str | None = None
    # Comma-separated name:key pairs, e.g. "returnpilot:sk-abc123,other:sk-xyz"
    API_KEYS: str | None = None

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    @property
    def default_countries_list(self) -> list[str]:
        return [c.strip() for c in self.DEFAULT_COUNTRIES.split(",") if c.strip()]

    @field_validator("PROXY_URL", "ALERT_WEBHOOK_URL", "SECRET_KEY",
                     "SERPER_API_KEY", "SERPAPI_KEY", "API_KEYS", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


settings = Settings()
