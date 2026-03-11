"""Google Shopping search via Serper.dev API.

Serper.dev provides a clean JSON API for Google Shopping results.
Free tier includes 2,500 searches. Set SERPER_API_KEY in .env.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

_SERPER_URL = "https://google.serper.dev/shopping"

# Map country codes to Serper gl/hl params
_COUNTRY_CONFIG = {
    "US": {"gl": "us", "hl": "en"},
    "AU": {"gl": "au", "hl": "en"},
    "GB": {"gl": "gb", "hl": "en"},
    "DE": {"gl": "de", "hl": "de"},
    "JP": {"gl": "jp", "hl": "ja"},
    "CA": {"gl": "ca", "hl": "en"},
    "FR": {"gl": "fr", "hl": "fr"},
    "IN": {"gl": "in", "hl": "en"},
    "BR": {"gl": "br", "hl": "pt"},
    "IT": {"gl": "it", "hl": "it"},
    "ES": {"gl": "es", "hl": "es"},
    "NL": {"gl": "nl", "hl": "nl"},
    "KR": {"gl": "kr", "hl": "ko"},
    "MX": {"gl": "mx", "hl": "es"},
    "SE": {"gl": "se", "hl": "sv"},
    "NZ": {"gl": "nz", "hl": "en"},
    "SG": {"gl": "sg", "hl": "en"},
}

_COUNTRY_CURRENCY = {
    "US": "USD", "AU": "AUD", "GB": "GBP", "DE": "EUR", "JP": "JPY",
    "CA": "CAD", "FR": "EUR", "IN": "INR", "BR": "BRL", "IT": "EUR",
    "ES": "EUR", "NL": "EUR", "KR": "KRW", "MX": "MXN", "SE": "SEK",
    "NZ": "NZD", "SG": "SGD",
}


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        return host.removeprefix("www.") or None
    except Exception:
        return None


async def serper_shopping_search(
    query: str,
    country_code: str = "US",
    num_results: int = 40,
) -> list[dict[str, Any]]:
    """Search Google Shopping via Serper.dev API.

    Returns list of product dicts in the same format as the Playwright scraper.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key:
        raise ValueError("SERPER_API_KEY not configured")

    cc = country_code.upper()
    config = _COUNTRY_CONFIG.get(cc, {"gl": "us", "hl": "en"})
    currency = _COUNTRY_CURRENCY.get(cc, "USD")

    payload = {
        "q": query,
        "gl": config["gl"],
        "hl": config["hl"],
        "num": min(num_results, 100),
    }

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    logger.info("Serper API search: query=%r country=%s", query, cc)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_SERPER_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    shopping_results = data.get("shopping", [])
    logger.info("Serper returned %d shopping results", len(shopping_results))

    results: list[dict[str, Any]] = []
    for item in shopping_results:
        price_str = item.get("price", "")
        # Serper returns price as string like "$499.99"
        price: float | None = None
        if price_str:
            import re
            nums = re.findall(r"[\d,]+\.?\d*", str(price_str))
            if nums:
                try:
                    price = float(nums[0].replace(",", ""))
                except ValueError:
                    pass

        link = item.get("link")

        results.append({
            "title": item.get("title"),
            "price": price,
            "currency": currency,
            "original_price": None,
            "store_name": item.get("source"),
            "store_link": link,
            "store_domain": _extract_domain(link),
            "product_link": link,
            "image_url": item.get("imageUrl") or item.get("thumbnail"),
            "shipping": item.get("delivery"),
            "condition": item.get("condition"),
            "rating": item.get("rating"),
            "review_count": item.get("ratingCount"),
        })

    return results
