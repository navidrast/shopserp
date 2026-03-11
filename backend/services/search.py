"""Search service -- orchestrates Google Shopping scraping across countries.

Runs concurrent scrapes with a semaphore to respect rate limits, and tags
each result with reputable-store metadata from the store registry.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.scraper.google_shopping import GoogleShoppingScraper
from backend.stores.registry import (
    COUNTRY_INFO,
    is_reputable_store,
)

logger = logging.getLogger(__name__)


class SearchService:
    """Facade for multi-country Google Shopping searches."""

    def __init__(self) -> None:
        self._scraper = GoogleShoppingScraper()
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)

    async def search(
        self,
        db: AsyncSession,
        query: str,
        countries: list[str],
        max_results: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        """Search Google Shopping across multiple countries concurrently.

        Args:
            db: Async database session (reserved for future caching).
            query: Search query string.
            countries: List of ISO 3166-1 alpha-2 country codes.
            max_results: Maximum results per country.

        Returns:
            Dict mapping country code to a list of result dicts.  Each
            result dict includes an ``is_reputable`` boolean flag.
        """
        if not countries:
            countries = settings.DEFAULT_COUNTRIES

        # Validate country codes
        valid_countries = [
            cc.upper() for cc in countries if cc.upper() in COUNTRY_INFO
        ]
        if not valid_countries:
            logger.warning(
                "No valid country codes in request: %s", countries,
            )
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
                logger.error(
                    "Search failed for country=%s: %s", cc, result,
                )
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
        """Scrape a single country with semaphore-controlled concurrency."""
        async with self._semaphore:
            logger.info(
                "Searching Google Shopping: query=%r country=%s max=%d",
                query,
                country_code,
                max_results,
            )
            raw_results = await self._scraper.search(
                query=query,
                country_code=country_code,
                num_results=max_results,
            )

        # Tag each result with reputable-store info
        tagged: list[dict[str, Any]] = []
        for item in raw_results:
            domain = item.get("store_domain", "")
            item["is_reputable"] = is_reputable_store(domain, country_code)
            tagged.append(item)

        logger.info(
            "Found %d results for country=%s (%d reputable)",
            len(tagged),
            country_code,
            sum(1 for r in tagged if r["is_reputable"]),
        )
        return tagged
