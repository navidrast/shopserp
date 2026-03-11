"""Async Google Shopping scraper with proxy rotation and rate-limit handling.

Usage::

    from backend.scraper.proxy import ProxyManager
    from backend.scraper.google_shopping import GoogleShoppingScraper

    pm = ProxyManager("http://user:pass@proxy:8080")
    scraper = GoogleShoppingScraper(proxy_manager=pm)
    results = await scraper.search("wireless headphones", country_code="US")
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.config import settings
from backend.scraper.parser import parse_price_comparison, parse_shopping_results
from backend.scraper.proxy import ProxyManager
from backend.scraper.user_agents import get_random_ua

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country-to-Google parameter mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CountryConfig:
    """Google Shopping query parameters for a specific country."""

    gl: str
    hl: str
    currency: str


COUNTRY_MAP: dict[str, CountryConfig] = {
    "US": CountryConfig(gl="us", hl="en", currency="USD"),
    "AU": CountryConfig(gl="au", hl="en", currency="AUD"),
    "GB": CountryConfig(gl="gb", hl="en", currency="GBP"),
    "DE": CountryConfig(gl="de", hl="de", currency="EUR"),
    "JP": CountryConfig(gl="jp", hl="ja", currency="JPY"),
    "CA": CountryConfig(gl="ca", hl="en", currency="CAD"),
    "FR": CountryConfig(gl="fr", hl="fr", currency="EUR"),
    "IN": CountryConfig(gl="in", hl="en", currency="INR"),
    "BR": CountryConfig(gl="br", hl="pt", currency="BRL"),
    "IT": CountryConfig(gl="it", hl="it", currency="EUR"),
    "ES": CountryConfig(gl="es", hl="es", currency="EUR"),
    "NL": CountryConfig(gl="nl", hl="nl", currency="EUR"),
    "KR": CountryConfig(gl="kr", hl="ko", currency="KRW"),
    "MX": CountryConfig(gl="mx", hl="es", currency="MXN"),
    "SE": CountryConfig(gl="se", hl="sv", currency="SEK"),
    "NZ": CountryConfig(gl="nz", hl="en", currency="NZD"),
    "SG": CountryConfig(gl="sg", hl="en", currency="SGD"),
}

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ScraperError(Exception):
    """Base exception for scraper errors."""


class CaptchaError(ScraperError):
    """Raised when Google serves a CAPTCHA instead of results."""


class RateLimitError(ScraperError):
    """Raised when retries are exhausted after repeated 429 responses."""


# ---------------------------------------------------------------------------
# Request configuration
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.google.com/search"
_MAX_RETRIES = 4
_BACKOFF_BASE = 3.0  # seconds; each retry doubles

# CAPTCHA detection strings commonly found in Google block pages.
_CAPTCHA_MARKERS: list[str] = [
    "detected unusual traffic",
    "/recaptcha/",
    "captcha",
    "sorry/index",
    "our systems have detected",
]


@dataclass
class _RequestStats:
    """Mutable counters used for debugging / monitoring."""

    total_requests: int = 0
    successful: int = 0
    rate_limited: int = 0
    captcha_blocked: int = 0
    errors: int = 0


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class GoogleShoppingScraper:
    """Async scraper for Google Shopping search results.

    Args:
        proxy_manager: Optional :class:`ProxyManager` instance for proxy
            rotation.  When ``None``, one is created from application
            settings.
        timeout: HTTP request timeout in seconds.  Defaults to the value
            in application settings.
    """

    def __init__(
        self,
        proxy_manager: ProxyManager | None = None,
        timeout: int | None = None,
    ) -> None:
        self._proxy_manager = proxy_manager or ProxyManager(settings.PROXY_URL)
        self._timeout = timeout or settings.REQUEST_TIMEOUT
        self._stats = _RequestStats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_headers(self, country_cfg: CountryConfig) -> dict[str, str]:
        """Return realistic browser headers for a single request."""
        ua = get_random_ua()
        accept_lang = f"{country_cfg.hl},en;q=0.9,*;q=0.5"
        return {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": accept_lang,
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            # Cookie-consent bypass -- tells Google we accepted the GDPR banner.
            "Cookie": "CONSENT=YES+; SOCS=CAESEwgDEgk2NjMxNTcxMjAaAmVuIAEaBgiA_LyaBg",
        }

    @staticmethod
    def _detect_captcha(html: str) -> bool:
        """Return ``True`` when the response body looks like a CAPTCHA page."""
        lower = html.lower()
        return any(marker in lower for marker in _CAPTCHA_MARKERS)

    async def _fetch(self, url: str, country_cfg: CountryConfig) -> str:
        """Fetch a URL with retries, backoff, and CAPTCHA detection.

        Returns the response body as a string.

        Raises:
            CaptchaError: If a CAPTCHA page is detected.
            RateLimitError: If retries are exhausted after 429 responses.
            ScraperError: For other unrecoverable HTTP errors.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            self._stats.total_requests += 1
            headers = self._build_headers(country_cfg)
            proxy = (
                self._proxy_manager.get_proxy()
                if self._proxy_manager.has_proxies
                else None
            )

            logger.debug(
                "Request attempt %d/%d  url=%s  proxy=%s",
                attempt + 1,
                _MAX_RETRIES,
                url,
                "direct" if proxy is None else "proxied",
            )

            try:
                async with httpx.AsyncClient(
                    proxy=proxy,
                    timeout=httpx.Timeout(self._timeout),
                    follow_redirects=True,
                    http2=True,
                ) as client:
                    response = await client.get(url, headers=headers)

                if response.status_code == 429:
                    self._stats.rate_limited += 1
                    wait = _BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning(
                        "Rate-limited (429) on attempt %d -- waiting %.1fs",
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                body = response.text

                if self._detect_captcha(body):
                    self._stats.captcha_blocked += 1
                    logger.error("CAPTCHA detected on attempt %d", attempt + 1)
                    raise CaptchaError(
                        "Google returned a CAPTCHA challenge. Consider using "
                        "proxies or reducing request frequency."
                    )

                self._stats.successful += 1
                return body

            except CaptchaError:
                raise
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                self._stats.errors += 1
                logger.error("HTTP %d: %s", exc.response.status_code, exc)
                wait = _BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait)
            except httpx.HTTPError as exc:
                last_exc = exc
                self._stats.errors += 1
                logger.error("HTTP error: %s", exc)
                wait = _BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait)

        if self._stats.rate_limited > 0:
            raise RateLimitError(
                f"Rate-limited {self._stats.rate_limited} times -- retries exhausted."
            )
        raise ScraperError(f"Failed after {_MAX_RETRIES} attempts: {last_exc}")

    def _build_search_url(
        self,
        query: str,
        country_cfg: CountryConfig,
        num: int = 40,
        start: int = 0,
    ) -> str:
        """Build the Google Shopping search URL."""
        params: dict[str, str | int] = {
            "q": query,
            "tbm": "shop",
            "gl": country_cfg.gl,
            "hl": country_cfg.hl,
            "num": min(num, 100),
            "pws": "0",
        }
        if start > 0:
            params["start"] = start
        return f"{_BASE_URL}?{urlencode(params)}"

    @staticmethod
    def _get_country_config(country_code: str) -> CountryConfig:
        """Resolve a country code to its Google params, with a safe default."""
        code = country_code.upper()
        if code in COUNTRY_MAP:
            return COUNTRY_MAP[code]
        logger.warning(
            "Unknown country code %r -- falling back to US defaults", code
        )
        return COUNTRY_MAP["US"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        country_code: str = "US",
        num_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Search Google Shopping and return parsed product results.

        Args:
            query: The search query string.
            country_code: Two-letter ISO country code (see ``COUNTRY_MAP``).
            num_results: Desired number of results.  Multiple pages are
                fetched when ``num_results`` exceeds a single page.

        Returns:
            A list of product dicts.  See :func:`parser.parse_shopping_results`
            for the dict schema.

        Raises:
            CaptchaError: If Google serves a CAPTCHA.
            RateLimitError: If 429 retries are exhausted.
            ScraperError: For other unrecoverable errors.
        """
        country_cfg = self._get_country_config(country_code)
        all_results: list[dict[str, Any]] = []

        # Google Shopping pages typically return up to 40 items.
        page_size = 40
        pages_needed = max(1, -(-num_results // page_size))  # ceil division

        for page_idx in range(pages_needed):
            start = page_idx * page_size

            url = self._build_search_url(
                query=query,
                country_cfg=country_cfg,
                num=page_size,
                start=start,
            )

            logger.info(
                "Fetching page %d (start=%d) for query=%r country=%s",
                page_idx + 1,
                start,
                query,
                country_code,
            )

            html = await self._fetch(url, country_cfg)
            page_results = parse_shopping_results(html, country_code)
            all_results.extend(page_results)

            logger.info(
                "Page %d yielded %d results (total so far: %d)",
                page_idx + 1,
                len(page_results),
                len(all_results),
            )

            # Stop early if the page returned nothing (no more results).
            if not page_results:
                logger.info("Empty page -- no more results available")
                break

            # Stop if we have enough.
            if len(all_results) >= num_results:
                break

            # Random delay between pages to avoid triggering rate limits.
            if page_idx < pages_needed - 1:
                delay = random.uniform(2.0, 5.0)
                logger.debug("Sleeping %.1fs before next page", delay)
                await asyncio.sleep(delay)

        # Trim to the requested count.
        trimmed = all_results[:num_results]
        logger.info(
            "Search complete: returning %d results for query=%r country=%s",
            len(trimmed),
            query,
            country_code,
        )
        return trimmed

    async def get_price_comparison(
        self,
        product_url: str,
        country_code: str = "US",
    ) -> list[dict[str, Any]]:
        """Fetch all seller prices for a specific Google Shopping product.

        Args:
            product_url: Full URL of the Google Shopping product/comparison
                page (e.g. ``https://www.google.com/shopping/product/...``).
            country_code: Two-letter ISO country code.

        Returns:
            A list of seller dicts.  See :func:`parser.parse_price_comparison`
            for the dict schema.

        Raises:
            CaptchaError: If Google serves a CAPTCHA.
            RateLimitError: If 429 retries are exhausted.
            ScraperError: For other unrecoverable errors.
        """
        country_cfg = self._get_country_config(country_code)

        # Ensure the URL includes the correct locale params.
        separator = "&" if "?" in product_url else "?"
        url = (
            f"{product_url}{separator}"
            f"gl={country_cfg.gl}&hl={country_cfg.hl}&pws=0"
        )

        logger.info("Fetching price comparison: %s", url)
        html = await self._fetch(url, country_cfg)
        sellers = parse_price_comparison(html, country_code)
        logger.info("Price comparison returned %d sellers", len(sellers))
        return sellers

    @property
    def stats(self) -> dict[str, int]:
        """Return a snapshot of request statistics for monitoring."""
        return {
            "total_requests": self._stats.total_requests,
            "successful": self._stats.successful,
            "rate_limited": self._stats.rate_limited,
            "captcha_blocked": self._stats.captcha_blocked,
            "errors": self._stats.errors,
        }
