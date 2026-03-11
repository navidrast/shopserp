"""Async Google Shopping scraper using Playwright headless browser.

Google Shopping requires JavaScript rendering — raw HTTP requests receive
a JS-loader stub instead of product results. This scraper uses Playwright
(headless Chromium) to fully render the page before extracting data.

Usage::

    scraper = GoogleShoppingScraper()
    results = await scraper.search("wireless headphones", country_code="US")
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from backend.config import settings
from backend.scraper.parser import parse_price_comparison, parse_shopping_results
from backend.scraper.user_agents import get_random_ua

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country-to-Google parameter mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CountryConfig:
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
# Exceptions
# ---------------------------------------------------------------------------


class ScraperError(Exception):
    """Base exception for scraper errors."""


class CaptchaError(ScraperError):
    """Raised when Google serves a CAPTCHA instead of results."""


class RateLimitError(ScraperError):
    """Raised when retries are exhausted after repeated 429 responses."""


_CAPTCHA_MARKERS: list[str] = [
    "detected unusual traffic",
    "/recaptcha/",
    "sorry/index",
    "our systems have detected",
]

_BASE_URL = "https://www.google.com/search"
_MAX_RETRIES = 3
_BACKOFF_BASE = 3.0


@dataclass
class _RequestStats:
    total_requests: int = 0
    successful: int = 0
    rate_limited: int = 0
    captcha_blocked: int = 0
    errors: int = 0


# ---------------------------------------------------------------------------
# Browser pool — reuse a single browser instance across scrapes
# ---------------------------------------------------------------------------

_browser_lock = asyncio.Lock()
_browser = None
_playwright = None


async def _get_browser():
    """Get or create a shared Playwright browser instance."""
    global _browser, _playwright
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--no-first-run",
                    "--disable-sync",
                ],
            )
            logger.info("Playwright Chromium browser launched")
        return _browser


async def close_browser():
    """Close the shared browser (call on app shutdown)."""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class GoogleShoppingScraper:
    def __init__(self, timeout: int | None = None) -> None:
        self._timeout = timeout or settings.REQUEST_TIMEOUT
        self._stats = _RequestStats()

    @staticmethod
    def _detect_captcha(html: str) -> bool:
        lower = html.lower()
        return any(marker in lower for marker in _CAPTCHA_MARKERS)

    @staticmethod
    def _is_js_stub(html: str) -> bool:
        """Detect if the response is a JS-loader stub without real content."""
        return (
            len(html) < 200000
            and "not redirected within" in html.lower()
            and "<noscript>" in html.lower()
        )

    def _build_search_url(
        self,
        query: str,
        country_cfg: CountryConfig,
        num: int = 40,
        start: int = 0,
    ) -> str:
        """Build Google Shopping URL using udm=28 (current Shopping param)."""
        params: dict[str, str | int] = {
            "q": query,
            "udm": "28",
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
        code = country_code.upper()
        if code in COUNTRY_MAP:
            return COUNTRY_MAP[code]
        logger.warning("Unknown country %r, falling back to US", code)
        return COUNTRY_MAP["US"]

    async def _fetch_with_playwright(self, url: str, country_cfg: CountryConfig) -> str:
        """Fetch a URL using headless Chromium, returning fully rendered HTML."""
        browser = await _get_browser()
        ua = get_random_ua()

        context = await browser.new_context(
            user_agent=ua,
            locale=country_cfg.hl,
            extra_http_headers={
                "Accept-Language": f"{country_cfg.hl},en;q=0.9",
            },
            java_script_enabled=True,
            bypass_csp=True,
        )
        # Set consent cookies to bypass GDPR banners
        await context.add_cookies([
            {"name": "CONSENT", "value": "YES+", "domain": ".google.com", "path": "/"},
            {"name": "SOCS", "value": "CAESEwgDEgk2NjMxNTcxMjAaAmVuIAEaBgiA_LyaBg", "domain": ".google.com", "path": "/"},
        ])

        page = await context.new_page()

        try:
            self._stats.total_requests += 1
            logger.info("Playwright fetching: %s", url)

            response = await page.goto(url, wait_until="networkidle", timeout=self._timeout * 1000)

            if response and response.status == 429:
                self._stats.rate_limited += 1
                raise RateLimitError("Google returned 429 (rate limited)")

            # Wait for shopping results to appear — try multiple selectors
            try:
                await page.wait_for_selector(
                    "div[data-docid], .sh-dgr__content, .sh-pr__product-results, "
                    "[data-sh-sr], .xcR77, div.i0X6df, div.KZmu8e",
                    timeout=8000,
                )
            except Exception:
                # Results may have loaded under a different selector, continue
                logger.debug("No known product selector found, extracting HTML anyway")

            # Extra wait for dynamic content
            await page.wait_for_timeout(1500)

            html = await page.content()

            if self._detect_captcha(html):
                self._stats.captcha_blocked += 1
                raise CaptchaError("Google returned a CAPTCHA challenge")

            self._stats.successful += 1
            logger.info("Playwright got %d bytes of HTML", len(html))
            return html

        finally:
            await page.close()
            await context.close()

    async def _fetch(self, url: str, country_cfg: CountryConfig) -> str:
        """Fetch with retries and backoff."""
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                html = await self._fetch_with_playwright(url, country_cfg)

                # If we got a JS stub instead of real content, retry
                if self._is_js_stub(html):
                    logger.warning("Got JS stub on attempt %d, retrying...", attempt + 1)
                    await asyncio.sleep(_BACKOFF_BASE * (attempt + 1))
                    continue

                return html

            except CaptchaError:
                raise
            except RateLimitError:
                wait = _BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 2)
                logger.warning("Rate limited, waiting %.1fs", wait)
                await asyncio.sleep(wait)
            except Exception as exc:
                last_exc = exc
                self._stats.errors += 1
                logger.error("Fetch error attempt %d: %s", attempt + 1, exc)
                await asyncio.sleep(_BACKOFF_BASE * (attempt + 1))

        raise ScraperError(f"Failed after {_MAX_RETRIES} attempts: {last_exc}")

    async def search(
        self,
        query: str,
        country_code: str = "US",
        num_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Search Google Shopping and return parsed product results."""
        country_cfg = self._get_country_config(country_code)
        all_results: list[dict[str, Any]] = []

        page_size = 40
        pages_needed = max(1, -(-num_results // page_size))

        for page_idx in range(pages_needed):
            start = page_idx * page_size
            url = self._build_search_url(query, country_cfg, page_size, start)

            logger.info(
                "Fetching page %d (start=%d) for query=%r country=%s",
                page_idx + 1, start, query, country_code,
            )

            html = await self._fetch(url, country_cfg)
            page_results = parse_shopping_results(html, country_code)
            all_results.extend(page_results)

            logger.info(
                "Page %d yielded %d results (total: %d)",
                page_idx + 1, len(page_results), len(all_results),
            )

            if not page_results:
                logger.info("Empty page — no more results")
                break

            if len(all_results) >= num_results:
                break

            if page_idx < pages_needed - 1:
                delay = random.uniform(2.0, 5.0)
                await asyncio.sleep(delay)

        trimmed = all_results[:num_results]
        logger.info("Search complete: %d results for %r in %s", len(trimmed), query, country_code)
        return trimmed

    async def get_price_comparison(
        self,
        product_url: str,
        country_code: str = "US",
    ) -> list[dict[str, Any]]:
        """Fetch all seller prices for a specific Google Shopping product."""
        country_cfg = self._get_country_config(country_code)
        sep = "&" if "?" in product_url else "?"
        url = f"{product_url}{sep}gl={country_cfg.gl}&hl={country_cfg.hl}&pws=0"

        logger.info("Fetching price comparison: %s", url)
        html = await self._fetch(url, country_cfg)
        sellers = parse_price_comparison(html, country_code)
        logger.info("Price comparison: %d sellers", len(sellers))
        return sellers

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total_requests": self._stats.total_requests,
            "successful": self._stats.successful,
            "rate_limited": self._stats.rate_limited,
            "captcha_blocked": self._stats.captcha_blocked,
            "errors": self._stats.errors,
        }
