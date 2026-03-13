"""Search service -- orchestrates Google Shopping scraping across countries.

Supports multiple backends in priority order:
1. Serper.dev API (if SERPER_API_KEY configured) — most reliable
2. Playwright headless browser (if no API key) — free but needs proxy for datacenter IPs
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.stores.registry import (
    COUNTRY_INFO,
    is_reputable_store,
    is_reputable_store_by_name,
    find_domain_by_store_name,
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
            countries = settings.default_countries_list

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
            store_name = item.get("store_name", "")
            reputable = is_reputable_store(domain, country_code)
            # Fallback: match by store name (Serper returns google.com redirect links)
            if not reputable and store_name:
                reputable = is_reputable_store_by_name(store_name, country_code)
                if reputable and (not domain or domain == "google.com"):
                    found_domain = find_domain_by_store_name(store_name)
                    if found_domain:
                        item["store_domain"] = found_domain
            item["is_reputable"] = reputable
            tagged.append(item)

        logger.info(
            "Found %d results for country=%s (%d reputable)",
            len(tagged), country_code,
            sum(1 for r in tagged if r["is_reputable"]),
        )
        return tagged

    # ── Structured search (v1 API) ────────────────────────────────────────────

    @staticmethod
    def build_search_queries(
        *,
        query: str | None = None,
        upc: str | None = None,
        part_number: str | None = None,
        sku: str | None = None,
        brand: str | None = None,
        model: str | None = None,
    ) -> list[str]:
        """Build a prioritized list of search queries from structured fields.

        Returns queries in cascade order — caller should try each until results
        are found. UPC/EAN is the most precise, then MPN, then brand+model,
        then free-text fallback.
        """
        queries: list[str] = []

        if upc:
            queries.append(upc)

        if part_number:
            prefix = f"{brand} " if brand else ""
            queries.append(f"{prefix}{part_number}")

        if brand and model:
            queries.append(f"{brand} {model}")
        elif model:
            queries.append(model)

        if query:
            queries.append(query)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for q in queries:
            q_lower = q.strip().lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique.append(q.strip())
        return unique

    @staticmethod
    def filter_results(
        results: list[dict[str, Any]],
        *,
        brand: str | None = None,
        model: str | None = None,
        condition: str | None = None,
    ) -> list[dict[str, Any]]:
        """Post-filter search results by brand, model, and/or condition."""
        filtered = results

        if brand:
            brand_lower = brand.lower()
            filtered = [
                r for r in filtered
                if brand_lower in (r.get("title") or "").lower()
                or brand_lower in (r.get("store_name") or "").lower()
            ]

        if model:
            model_lower = model.lower()
            # For model matching, normalize whitespace and allow flexible matching
            model_tokens = model_lower.split()
            filtered = [
                r for r in filtered
                if all(tok in (r.get("title") or "").lower() for tok in model_tokens)
            ]

        if condition and condition != "any":
            cond_lower = condition.lower()
            filtered = [
                r for r in filtered
                if (r.get("condition") or "").lower() == cond_lower
                # Keep results with no condition info if filtering for "new"
                # (most listings without explicit condition are new)
                or (cond_lower == "new" and not r.get("condition"))
            ]

        return filtered

    async def structured_search(
        self,
        db: AsyncSession,
        *,
        query: str | None = None,
        upc: str | None = None,
        part_number: str | None = None,
        sku: str | None = None,
        brand: str | None = None,
        model: str | None = None,
        condition: str | None = None,
        countries: list[str],
        max_results: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        """Search with structured identifiers and cascading fallback.

        Tries each query in priority order (UPC → MPN → brand+model → free text)
        and returns the first set that yields results after filtering.
        """
        search_queries = self.build_search_queries(
            query=query, upc=upc, part_number=part_number,
            sku=sku, brand=brand, model=model,
        )

        if not search_queries:
            logger.warning("No search terms provided")
            return {}

        for i, q in enumerate(search_queries):
            logger.info(
                "Structured search attempt %d/%d: query=%r",
                i + 1, len(search_queries), q,
            )
            grouped = await self.search(
                db=db, query=q, countries=countries, max_results=max_results,
            )

            # Apply post-filters
            filtered_grouped: dict[str, list[dict[str, Any]]] = {}
            total_filtered = 0
            for cc, items in grouped.items():
                filtered = self.filter_results(
                    items, brand=brand, model=model, condition=condition,
                )
                filtered_grouped[cc] = filtered
                total_filtered += len(filtered)

            if total_filtered > 0:
                logger.info(
                    "Structured search succeeded on attempt %d: query=%r, %d results after filtering",
                    i + 1, q, total_filtered,
                )
                return filtered_grouped

            logger.info(
                "Attempt %d yielded 0 results after filtering, trying next query",
                i + 1,
            )

        # All queries exhausted — return unfiltered results from the last attempt
        # as a best-effort fallback
        logger.warning("All structured search queries exhausted, returning last unfiltered results")
        return grouped if grouped else {}

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
