"""Search service -- orchestrates Google Shopping scraping across countries.

Supports multiple backends in priority order:
1. Serper.dev API (if SERPER_API_KEY configured) — most reliable
2. Playwright headless browser (if no API key) — free but needs proxy for datacenter IPs
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.stores.registry import (
    COUNTRY_INFO,
    is_reputable_store,
)

logger = logging.getLogger(__name__)


class SearchService:
    """Facade for multi-country Google Shopping searches."""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)
        self._backend = self._detect_backend()
        logger.info("Search backend: %s", self._backend)

    @staticmethod
    def _detect_backend() -> str:
        if settings.SERPER_API_KEY:
            return "serper"
        if settings.SERPAPI_KEY:
            return "serpapi"
        return "playwright"

    async def search(
        self,
        db: AsyncSession,
        query: str,
        countries: list[str],
        max_results: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        if not countries:
            countries = settings.DEFAULT_COUNTRIES

        valid_countries = [
            cc.upper() for cc in countries if cc.upper() in COUNTRY_INFO
        ]
        if not valid_countries:
            logger.warning("No valid country codes: %s", countries)
            return {}

        per_country = max(1, min(max_results, 100))

        tasks = [
            self._search_country(query, cc, per_country)
            for cc in valid_countries
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        grouped: dict[str, list[dict[str, Any]]] = {}
        for cc, result in zip(valid_countries, results_list):
            if isinstance(result, BaseException):
                logger.error("Search failed for country=%s: %s", cc, result)
                grouped[cc] = []
            else:
                grouped[cc] = result

        return grouped

    async def _search_country(
        self,
        query: str,
        country_code: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Search a single country using the configured backend."""
        async with self._semaphore:
            logger.info(
                "Searching [%s]: query=%r country=%s max=%d",
                self._backend, query, country_code, max_results,
            )

            if self._backend == "serper":
                raw_results = await self._search_serper(query, country_code, max_results)
            elif self._backend == "serpapi":
                raw_results = await self._search_serpapi(query, country_code, max_results)
            else:
                raw_results = await self._search_playwright(query, country_code, max_results)

        # Tag each result with reputable-store info
        tagged: list[dict[str, Any]] = []
        for item in raw_results:
            domain = item.get("store_domain", "")
            item["is_reputable"] = is_reputable_store(domain, country_code)
            tagged.append(item)

        logger.info(
            "Found %d results for country=%s (%d reputable)",
            len(tagged), country_code,
            sum(1 for r in tagged if r["is_reputable"]),
        )
        return tagged

    @staticmethod
    async def _search_serper(query: str, country_code: str, max_results: int) -> list[dict[str, Any]]:
        from backend.scraper.serper_api import serper_shopping_search
        return await serper_shopping_search(query, country_code, max_results)

    @staticmethod
    async def _search_serpapi(query: str, country_code: str, max_results: int) -> list[dict[str, Any]]:
        """SerpAPI fallback (similar JSON API)."""
        import httpx
        api_key = settings.SERPAPI_KEY
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": country_code.lower(),
            "hl": "en",
            "num": min(max_results, 100),
            "api_key": api_key,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("shopping_results", []):
            price = item.get("extracted_price")
            link = item.get("link")
            from urllib.parse import urlparse
            domain = urlparse(link).hostname.removeprefix("www.") if link else None
            results.append({
                "title": item.get("title"),
                "price": price,
                "currency": item.get("currency", "USD"),
                "original_price": item.get("extracted_old_price"),
                "store_name": item.get("source"),
                "store_link": link,
                "store_domain": domain,
                "product_link": link,
                "image_url": item.get("thumbnail"),
                "shipping": item.get("delivery"),
                "condition": item.get("second_hand_condition"),
                "rating": item.get("rating"),
                "review_count": item.get("reviews"),
            })
        return results

    @staticmethod
    async def _search_playwright(query: str, country_code: str, max_results: int) -> list[dict[str, Any]]:
        from backend.scraper.google_shopping import GoogleShoppingScraper
        scraper = GoogleShoppingScraper()
        return await scraper.search(query, country_code, max_results)
