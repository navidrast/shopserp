"""Parse Google Shopping HTML into structured product dictionaries.

Google frequently changes its DOM structure, so this module tries multiple
selector strategies and falls back gracefully when elements are missing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------

# Maps common currency symbols / prefixes to ISO codes.  Used as a fallback
# when the country-level currency is not known.
_SYMBOL_TO_CURRENCY: dict[str, str] = {
    "$": "USD",
    "US$": "USD",
    "A$": "AUD",
    "AU$": "AUD",
    "C$": "CAD",
    "CA$": "CAD",
    "NZ$": "NZD",
    "S$": "SGD",
    "MX$": "MXN",
    "R$": "BRL",
    "\u20ac": "EUR",  # Euro sign
    "\u00a3": "GBP",  # Pound sign
    "\u00a5": "JPY",  # Yen sign
    "\uffe5": "JPY",
    "\u20a9": "KRW",  # Won sign
    "\u20b9": "INR",  # Rupee sign
    "kr": "SEK",
    "SEK": "SEK",
}

_COUNTRY_CURRENCY: dict[str, str] = {
    "US": "USD",
    "AU": "AUD",
    "GB": "GBP",
    "DE": "EUR",
    "JP": "JPY",
    "CA": "CAD",
    "FR": "EUR",
    "IN": "INR",
    "BR": "BRL",
    "IT": "EUR",
    "ES": "EUR",
    "NL": "EUR",
    "KR": "KRW",
    "MX": "MXN",
    "SE": "SEK",
    "NZ": "NZD",
    "SG": "SGD",
}

# Regex that captures an optional currency prefix/symbol, the numeric part
# (with decimals and thousands separators), and an optional suffix symbol.
_PRICE_RE = re.compile(
    r"(?P<prefix>[A-Z]{1,3}\$|[A-Z]{2,3}|[\$\u20ac\u00a3\u00a5\uffe5\u20a9\u20b9]|kr\.?\s?)?"
    r"\s*"
    r"(?P<number>[\d.,\s\u00a0]+)"
    r"\s*"
    r"(?P<suffix>[A-Z]{2,3})?",
    re.UNICODE,
)


def _parse_price(raw: str | None, country_code: str) -> tuple[float | None, str | None]:
    """Extract a numeric price and currency code from a raw price string.

    Returns ``(price_float, currency_iso_code)`` or ``(None, None)`` when
    parsing fails.
    """
    if not raw:
        return None, None

    raw = raw.strip()
    match = _PRICE_RE.search(raw)
    if not match:
        return None, None

    prefix = (match.group("prefix") or "").strip()
    suffix = (match.group("suffix") or "").strip()
    number_str = match.group("number").strip()

    # Determine currency from prefix, suffix, or country fallback
    currency: str | None = None
    for token in (prefix, suffix):
        if token in _SYMBOL_TO_CURRENCY:
            currency = _SYMBOL_TO_CURRENCY[token]
            break
    if currency is None:
        currency = _COUNTRY_CURRENCY.get(country_code.upper())

    # Normalise the number string.
    # European formats use '.' for thousands and ',' for decimals.
    # We detect the convention by looking at the last separator.
    number_str = number_str.replace("\u00a0", "").replace(" ", "")

    if "," in number_str and "." in number_str:
        # Both separators present -- last one is the decimal separator.
        if number_str.rfind(",") > number_str.rfind("."):
            # European: 1.234,56
            number_str = number_str.replace(".", "").replace(",", ".")
        else:
            # US/UK: 1,234.56
            number_str = number_str.replace(",", "")
    elif "," in number_str:
        # Could be thousands (1,234) or decimal (12,34).
        parts = number_str.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely a decimal comma (European single-value price).
            number_str = number_str.replace(",", ".")
        else:
            number_str = number_str.replace(",", "")

    try:
        value = float(number_str)
    except ValueError:
        return None, currency

    return value, currency


def _extract_domain(url: str | None) -> str | None:
    """Extract the bare domain from a full URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Strip leading "www."
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _extract_google_redirect_url(href: str | None) -> str | None:
    """Unwrap a Google redirect (``/url?q=...``) to the real destination."""
    if not href:
        return None
    if href.startswith("/url"):
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        real = qs.get("q") or qs.get("url")
        if real:
            return real[0]
    if href.startswith("http"):
        return href
    return None


def _safe_text(tag: Tag | None) -> str | None:
    """Return stripped text content or None."""
    if tag is None:
        return None
    text = tag.get_text(strip=True)
    return text if text else None


def _safe_attr(tag: Tag | None, attr: str) -> str | None:
    """Return an attribute value or None."""
    if tag is None:
        return None
    val = tag.get(attr)
    if isinstance(val, list):
        val = val[0] if val else None
    return val if val else None


# ---------------------------------------------------------------------------
# JSON-LD extraction
# ---------------------------------------------------------------------------

def _extract_jsonld_products(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract Product entries from embedded JSON-LD ``<script>`` tags."""
    products: list[dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "Product":
                products.append(item)
            # Handle ItemList wrapping products
            if item.get("@type") == "ItemList":
                for elem in item.get("itemListElement", []):
                    if isinstance(elem, dict) and elem.get("@type") == "Product":
                        products.append(elem)
    return products


def _jsonld_to_result(item: dict[str, Any], country_code: str) -> dict[str, Any]:
    """Convert a JSON-LD Product dict to our canonical result dict."""
    offers = item.get("offers") or item.get("offer") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    price_raw = offers.get("price")
    currency = offers.get("priceCurrency") or _COUNTRY_CURRENCY.get(country_code.upper())
    try:
        price = float(price_raw) if price_raw is not None else None
    except (ValueError, TypeError):
        price, currency = _parse_price(str(price_raw), country_code)

    rating_obj = item.get("aggregateRating") or {}
    rating_val: float | None = None
    review_count: int | None = None
    try:
        rating_val = float(rating_obj.get("ratingValue", 0)) or None
    except (ValueError, TypeError):
        pass
    try:
        review_count = int(rating_obj.get("reviewCount") or rating_obj.get("ratingCount") or 0) or None
    except (ValueError, TypeError):
        pass

    return {
        "title": item.get("name"),
        "price": price,
        "currency": currency,
        "original_price": None,
        "store_name": (offers.get("seller") or {}).get("name") if isinstance(offers.get("seller"), dict) else offers.get("seller"),
        "store_link": offers.get("url"),
        "store_domain": _extract_domain(offers.get("url")),
        "product_link": item.get("url") or offers.get("url"),
        "image_url": item.get("image"),
        "shipping": None,
        "condition": offers.get("itemCondition"),
        "rating": rating_val,
        "review_count": review_count,
    }


# ---------------------------------------------------------------------------
# CSS-selector based extraction strategies
# ---------------------------------------------------------------------------

# Each strategy is a tuple of (container_selector, field_extractors).
# The first strategy that finds at least one container wins.

def _strategy_grid(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Parse the grid/card layout (``.sh-dgr__gr-auto``)."""
    containers = soup.select(".sh-dgr__gr-auto, .sh-dgr__content")
    results: list[dict[str, Any]] = []
    for card in containers:
        result = _extract_from_card(card, country_code)
        if result.get("title"):
            results.append(result)
    return results


def _strategy_list(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Parse the list/row layout (``.sh-dlr__list-result``)."""
    containers = soup.select(".sh-dlr__list-result")
    results: list[dict[str, Any]] = []
    for card in containers:
        result = _extract_from_card(card, country_code)
        if result.get("title"):
            results.append(result)
    return results


def _strategy_docid(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Parse product cards identified by ``[data-docid]``."""
    containers = soup.select("[data-docid]")
    results: list[dict[str, Any]] = []
    for card in containers:
        result = _extract_from_card(card, country_code)
        if result.get("title"):
            results.append(result)
    return results


def _strategy_generic_divs(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Broad fallback: find divs that look like product cards."""
    containers = soup.select(
        "[data-sh-gr], .sh-pr__product-results-grid div[data-docid], "
        ".KZmu8e, .i0X6df, .u30d4, .mnIHsc"
    )
    results: list[dict[str, Any]] = []
    for card in containers:
        result = _extract_from_card(card, country_code)
        if result.get("title"):
            results.append(result)
    return results


def _strategy_rendered_shopping(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Parse Playwright-rendered Google Shopping page (udm=28 format).

    After JS rendering, product cards contain visible text with prices,
    store names, and product titles in aria-labels and standard elements.
    """
    results: list[dict[str, Any]] = []

    # Strategy A: Look for product cards with aria-label containing price info
    # Google Shopping rendered cards often have aria-label on the outer div
    for card in soup.select("[data-docid]"):
        result = _extract_from_card(card, country_code)
        if result.get("title"):
            results.append(result)

    if results:
        return results

    # Strategy B: Find product links to Google Shopping product pages
    product_links = soup.select("a[href*='/shopping/product/'], a[href*='shopping/product']")
    seen: set[str] = set()
    for link in product_links:
        href = link.get("href", "")
        if href in seen:
            continue
        seen.add(href)

        # Walk up to find the containing card
        card = link.parent
        for _ in range(5):
            if card and card.parent:
                card = card.parent
                # Stop at reasonable card boundary
                card_classes = " ".join(card.get("class", []))
                if any(c in card_classes for c in ("sh-dgr", "sh-dlr", "KZmu8e", "i0X6df")):
                    break
            else:
                break

        if card:
            result = _extract_from_card(card, country_code)
            if result.get("title"):
                results.append(result)

    if results:
        return results

    # Strategy C: Regex-based extraction from rendered text
    # Find all elements that look like product cards by content patterns
    # Look for elements containing a price pattern followed by a store name
    price_pattern = re.compile(
        r'[\$\€\£\¥A\$]?\s*\d[\d,]*\.?\d*'
    )

    for h3 in soup.find_all(["h3", "h4", "div[role='heading']"]):
        title = _safe_text(h3)
        if not title or len(title) < 3:
            continue

        # Look for price near this title (within parent/sibling elements)
        container = h3.parent
        if container:
            container = container.parent or container

        if not container:
            continue

        container_text = container.get_text(" ", strip=True)
        price_match = price_pattern.search(container_text)
        if not price_match:
            continue

        price, currency = _parse_price(price_match.group(), country_code)
        if price is None or price <= 0:
            continue

        # Try to find store name
        store_name = None
        for store_sel in (".aULzUe", ".IuHnof", ".E5ocAb", ".zPEcBd"):
            store_tag = container.select_one(store_sel)
            if store_tag:
                store_name = _safe_text(store_tag)
                break

        # Find a link
        link_tag = container.select_one("a[href]")
        raw_href = _safe_attr(link_tag, "href")
        product_link = _extract_google_redirect_url(raw_href) or raw_href

        # Image
        img_tag = container.select_one("img[src]")
        image_url = _safe_attr(img_tag, "src") or _safe_attr(img_tag, "data-src")

        results.append({
            "title": title,
            "price": price,
            "currency": currency,
            "original_price": None,
            "store_name": store_name,
            "store_link": None,
            "store_domain": _extract_domain(product_link),
            "product_link": product_link,
            "image_url": image_url,
            "shipping": None,
            "condition": None,
            "rating": None,
            "review_count": None,
        })

    return results


def _strategy_aria_labels(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Extract product data from aria-label attributes on cards.

    Rendered Google Shopping cards often have descriptive aria-labels like:
    'PlayStation 5 Console, $499.99, from Best Buy, 4.5 stars'
    """
    results: list[dict[str, Any]] = []
    price_re = re.compile(r'[\$\€\£\¥]\s*[\d,]+\.?\d*')

    for el in soup.find_all(attrs={"aria-label": True}):
        label = el.get("aria-label", "")
        if not label or len(label) < 10:
            continue

        # Must contain a price
        pm = price_re.search(label)
        if not pm:
            continue

        price, currency = _parse_price(pm.group(), country_code)
        if not price or price <= 0:
            continue

        # Split label into parts (usually comma-separated)
        parts = [p.strip() for p in label.split(",")]
        title = parts[0] if parts else None

        store_name = None
        for part in parts:
            if part.lower().startswith("from "):
                store_name = part[5:].strip()
                break

        # Get link
        link_tag = el if el.name == "a" else el.select_one("a[href]")
        raw_href = _safe_attr(link_tag, "href") if link_tag else None
        product_link = _extract_google_redirect_url(raw_href) or raw_href

        img_tag = el.select_one("img[src]")
        image_url = _safe_attr(img_tag, "src") if img_tag else None

        if title:
            results.append({
                "title": title,
                "price": price,
                "currency": currency,
                "original_price": None,
                "store_name": store_name,
                "store_link": None,
                "store_domain": _extract_domain(product_link),
                "product_link": product_link,
                "image_url": image_url,
                "shipping": None,
                "condition": None,
                "rating": None,
                "review_count": None,
            })

    return results


def _extract_from_card(card: Tag, country_code: str) -> dict[str, Any]:
    """Extract product fields from an individual card/row element.

    Tries multiple selectors per field for resilience.
    """
    # ── Title ──────────────────────────────────────────────────────
    title_tag = (
        card.select_one(".translate-content")
        or card.select_one("h3")
        or card.select_one("h4")
        or card.select_one("[role='heading']")
        or card.select_one(".Xjkr3b")
        or card.select_one(".tAxDx")
        or card.select_one(".EI11Pd")
    )
    title = _safe_text(title_tag)

    # ── Price ──────────────────────────────────────────────────────
    price_tag = (
        card.select_one(".a8Pemb")
        or card.select_one("[data-sh-or='price']")
        or card.select_one(".HRLxBb")
        or card.select_one(".kHxwFf")
        or card.select_one(".XrAfOe .a8Pemb")
        or card.select_one("span.a8Pemb")
        or card.select_one(".Nr22bf .a8Pemb")
    )
    price, currency = _parse_price(_safe_text(price_tag), country_code)

    # ── Original / strikethrough price ─────────────────────────────
    orig_price_tag = (
        card.select_one(".Tht1Kc")
        or card.select_one(".T14wmb")
        or card.select_one("[data-sh-or='originalPrice']")
        or card.select_one("span[style*='line-through']")
    )
    original_price, _ = _parse_price(_safe_text(orig_price_tag), country_code)

    # ── Store name ─────────────────────────────────────────────────
    store_tag = (
        card.select_one(".aULzUe")
        or card.select_one(".IuHnof")
        or card.select_one("[data-sh-or='merchant']")
        or card.select_one(".E5ocAb")
        or card.select_one(".b5ycib .zPEcBd")
    )
    store_name = _safe_text(store_tag)

    # ── Product link ───────────────────────────────────────────────
    link_tag = (
        card.select_one("a.shntl")
        or card.select_one("a.translate-content")
        or card.select_one("a[href*='/shopping/product/']")
        or card.select_one("a[href*='url?']")
        or card.select_one("a[data-what='1']")
    )
    if link_tag is None:
        # Fallback: first link wrapping the title
        link_tag = card.select_one("a[href]")

    raw_href = _safe_attr(link_tag, "href")
    product_link = _extract_google_redirect_url(raw_href) or raw_href

    # ── Store link / domain ────────────────────────────────────────
    store_link_tag = card.select_one("a.b5ycib") or card.select_one("a.shntl")
    store_link = _extract_google_redirect_url(_safe_attr(store_link_tag, "href"))
    store_domain = _extract_domain(store_link) or _extract_domain(product_link)

    # ── Image ──────────────────────────────────────────────────────
    img_tag = card.select_one("img[src]")
    image_url = _safe_attr(img_tag, "src") or _safe_attr(img_tag, "data-src")

    # ── Shipping info ──────────────────────────────────────────────
    shipping_tag = (
        card.select_one(".dD8iuc")
        or card.select_one("[data-sh-or='shipping']")
        or card.select_one(".SzjKtb")
        or card.select_one(".vEjMR")
    )
    shipping = _safe_text(shipping_tag)

    # ── Condition ──────────────────────────────────────────────────
    condition: str | None = None
    for cond_sel in (".LGq0Xe", ".Yy4wdb", "[data-sh-or='condition']"):
        cond_tag = card.select_one(cond_sel)
        if cond_tag:
            condition = _safe_text(cond_tag)
            break

    # ── Rating & review count ──────────────────────────────────────
    rating: float | None = None
    review_count: int | None = None

    rating_tag = card.select_one("[aria-label*='out of']") or card.select_one("[aria-label*='stars']")
    if rating_tag:
        label = _safe_attr(rating_tag, "aria-label") or ""
        nums = re.findall(r"[\d.]+", label)
        if nums:
            try:
                rating = float(nums[0])
            except ValueError:
                pass

    review_tag = (
        card.select_one(".NzUzee span")
        or card.select_one(".QhqGkb .z1asCe")
        or card.select_one("[aria-label*='review']")
    )
    if review_tag:
        review_text = _safe_text(review_tag) or _safe_attr(review_tag, "aria-label") or ""
        nums = re.findall(r"[\d,]+", review_text.replace(".", ""))
        if nums:
            try:
                review_count = int(nums[0].replace(",", ""))
            except ValueError:
                pass

    return {
        "title": title,
        "price": price,
        "currency": currency,
        "original_price": original_price,
        "store_name": store_name,
        "store_link": store_link,
        "store_domain": store_domain,
        "product_link": product_link,
        "image_url": image_url,
        "shipping": shipping,
        "condition": condition,
        "rating": rating,
        "review_count": review_count,
    }


# ---------------------------------------------------------------------------
# Price comparison (detail) page parser
# ---------------------------------------------------------------------------

def _parse_comparison_sellers(soup: BeautifulSoup, country_code: str) -> list[dict[str, Any]]:
    """Parse the *Compare prices from X stores* detail page."""
    results: list[dict[str, Any]] = []

    # Seller rows in the comparison table
    seller_selectors = [
        ".sh-osd__offer",           # newer layout
        ".sh-osd__offer-row",       # alternative
        ".online-offer-row",        # older layout
        ".sh-pr__seller-row",       # another variant
        "tr.sh-osd__offer",         # table-based layout
    ]

    rows: list[Tag] = []
    for sel in seller_selectors:
        rows = soup.select(sel)
        if rows:
            break

    for row in rows:
        # Seller / store name
        seller_tag = (
            row.select_one(".sh-osd__offer-store-name")
            or row.select_one(".kPMwsc")
            or row.select_one("[data-offer-store-name]")
            or row.select_one(".b5ycib")
        )
        store_name = _safe_text(seller_tag)
        if seller_tag and not store_name:
            store_name = _safe_attr(seller_tag, "data-offer-store-name")

        # Price
        price_tag = (
            row.select_one(".sh-osd__offer-price")
            or row.select_one(".drzWO")
            or row.select_one("[data-sh-or='price']")
        )
        price, currency = _parse_price(_safe_text(price_tag), country_code)

        # Total price (with shipping)
        total_tag = (
            row.select_one(".sh-osd__total-price")
            or row.select_one(".drzWO:last-child")
        )
        total_price_text = _safe_text(total_tag)
        total_price, _ = _parse_price(total_price_text, country_code)

        # Shipping
        shipping_tag = (
            row.select_one(".sh-osd__offer-shipping")
            or row.select_one("[data-sh-or='shipping']")
        )
        shipping = _safe_text(shipping_tag)

        # Link
        link_tag = row.select_one("a[href]")
        raw_href = _safe_attr(link_tag, "href")
        store_link = _extract_google_redirect_url(raw_href) or raw_href

        # Condition
        condition_tag = row.select_one(".sh-osd__offer-condition") or row.select_one(".LGq0Xe")
        condition = _safe_text(condition_tag)

        results.append({
            "store_name": store_name,
            "price": price,
            "currency": currency,
            "total_price": total_price,
            "shipping": shipping,
            "store_link": store_link,
            "store_domain": _extract_domain(store_link),
            "condition": condition,
        })

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_shopping_results(
    html: str,
    country_code: str,
) -> list[dict[str, Any]]:
    """Parse Google Shopping HTML into a list of product result dicts.

    Args:
        html: Raw HTML response body from Google Shopping.
        country_code: Two-letter ISO country code (e.g. ``"US"``, ``"DE"``).
            Used for currency inference and locale-aware price parsing.

    Returns:
        A list of dicts, each containing:
        ``title``, ``price``, ``currency``, ``original_price``,
        ``store_name``, ``store_link``, ``store_domain``,
        ``product_link``, ``image_url``, ``shipping``, ``condition``,
        ``rating``, ``review_count``.
        Missing fields are set to ``None``.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []

    # Try CSS-selector strategies in order of specificity.
    strategies = [
        _strategy_grid,
        _strategy_list,
        _strategy_docid,
        _strategy_generic_divs,
        _strategy_rendered_shopping,
        _strategy_aria_labels,
    ]

    for strategy in strategies:
        results = strategy(soup, country_code)
        if results:
            logger.debug(
                "Strategy %s matched %d results", strategy.__name__, len(results)
            )
            break

    # Supplement with JSON-LD data when CSS extraction found nothing.
    if not results:
        jsonld_products = _extract_jsonld_products(soup)
        if jsonld_products:
            logger.debug("Falling back to JSON-LD extraction (%d items)", len(jsonld_products))
            results = [_jsonld_to_result(p, country_code) for p in jsonld_products]

    # De-duplicate by title (keep first occurrence).
    seen_titles: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in results:
        key = (r.get("title") or "").lower().strip()
        if key and key in seen_titles:
            continue
        if key:
            seen_titles.add(key)
        deduped.append(r)

    logger.info("Parsed %d unique product results from HTML", len(deduped))
    return deduped


def parse_price_comparison(
    html: str,
    country_code: str,
) -> list[dict[str, Any]]:
    """Parse a Google Shopping *price comparison* detail page.

    Args:
        html: Raw HTML of the comparison page.
        country_code: Two-letter ISO country code.

    Returns:
        A list of seller dicts containing ``store_name``, ``price``,
        ``currency``, ``total_price``, ``shipping``, ``store_link``,
        ``store_domain``, and ``condition``.
    """
    soup = BeautifulSoup(html, "lxml")
    results = _parse_comparison_sellers(soup, country_code)
    logger.info("Parsed %d sellers from price comparison page", len(results))
    return results
