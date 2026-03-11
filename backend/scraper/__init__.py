"""ShopSerp Google Shopping scraper engine."""

from backend.scraper.google_shopping import (
    CaptchaError,
    GoogleShoppingScraper,
    RateLimitError,
    ScraperError,
)
from backend.scraper.parser import parse_price_comparison, parse_shopping_results
from backend.scraper.proxy import ProxyManager
from backend.scraper.user_agents import get_random_ua

__all__ = [
    "CaptchaError",
    "GoogleShoppingScraper",
    "ProxyManager",
    "RateLimitError",
    "ScraperError",
    "get_random_ua",
    "parse_price_comparison",
    "parse_shopping_results",
]
