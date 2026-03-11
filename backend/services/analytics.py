"""Analytics service -- price statistics, history, and store breakdowns.

Provides aggregated analytics over :class:`PriceRecord` rows, including
summary statistics, time-series history, per-store breakdowns, and price
distribution buckets.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Monitor, PriceRecord, Product

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Compute price analytics from stored price records."""

    # ------------------------------------------------------------------
    # Per-monitor analytics
    # ------------------------------------------------------------------

    async def get_price_analytics(
        self,
        db: AsyncSession,
        monitor_id: int,
        days: int = 30,
    ) -> dict[str, Any]:
        """Calculate comprehensive price analytics for a monitor.

        Args:
            db: Async database session.
            monitor_id: PK of the monitor.
            days: Look-back window in days.

        Returns:
            Dict with keys ``current``, ``reputable_only``,
            ``price_history``, ``store_breakdown``, and
            ``price_distribution``.

        Raises:
            ValueError: If the monitor does not exist.
        """
        # Verify monitor exists
        stmt = select(Monitor).where(Monitor.id == monitor_id)
        result = await db.execute(stmt)
        monitor = result.scalar_one_or_none()
        if monitor is None:
            raise ValueError(f"Monitor {monitor_id} not found")

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(PriceRecord)
            .where(
                PriceRecord.monitor_id == monitor_id,
                PriceRecord.scraped_at >= cutoff,
            )
            .order_by(PriceRecord.scraped_at.asc())
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        all_prices = [r.price for r in records]
        reputable_prices = [r.price for r in records if r.is_reputable]

        return {
            "monitor_id": monitor_id,
            "days": days,
            "current": _compute_stats(all_prices),
            "reputable_only": _compute_stats(reputable_prices),
            "price_history": _build_price_history(records),
            "store_breakdown": _build_store_breakdown(records),
            "price_distribution": _build_price_distribution(all_prices),
        }

    # ------------------------------------------------------------------
    # Per-product history (across all countries)
    # ------------------------------------------------------------------

    async def get_price_history(
        self,
        db: AsyncSession,
        product_id: int,
        days: int = 90,
    ) -> dict[str, Any]:
        """Get price history across all countries for a product.

        Args:
            db: Async database session.
            product_id: PK of the product.
            days: Look-back window in days.

        Returns:
            Dict keyed by country code, each containing a time-series of
            daily aggregate prices.

        Raises:
            ValueError: If the product does not exist.
        """
        stmt = (
            select(Product)
            .options(selectinload(Product.monitors))
            .where(Product.id == product_id)
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        by_country: dict[str, list[dict[str, Any]]] = {}

        for monitor in product.monitors:
            stmt = (
                select(PriceRecord)
                .where(
                    PriceRecord.monitor_id == monitor.id,
                    PriceRecord.scraped_at >= cutoff,
                )
                .order_by(PriceRecord.scraped_at.asc())
            )
            result = await db.execute(stmt)
            records = list(result.scalars().all())
            by_country[monitor.country_code] = _build_price_history(records)

        return {
            "product_id": product_id,
            "product_name": product.name,
            "days": days,
            "countries": by_country,
        }

    # ------------------------------------------------------------------
    # Store comparison for a monitor
    # ------------------------------------------------------------------

    async def get_store_comparison(
        self,
        db: AsyncSession,
        monitor_id: int,
    ) -> dict[str, Any]:
        """Compare current prices across stores for a monitor.

        Returns:
            Dict with a ``stores`` list containing per-store price info
            sorted by current price ascending.

        Raises:
            ValueError: If the monitor does not exist.
        """
        stmt = select(Monitor).where(Monitor.id == monitor_id)
        result = await db.execute(stmt)
        monitor = result.scalar_one_or_none()
        if monitor is None:
            raise ValueError(f"Monitor {monitor_id} not found")

        # Fetch only the most recent batch of records
        stmt = (
            select(PriceRecord)
            .where(PriceRecord.monitor_id == monitor_id)
            .order_by(PriceRecord.scraped_at.desc())
            .limit(200)
        )
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return {"monitor_id": monitor_id, "stores": []}

        # Determine the latest scrape batch (records within 60s of newest)
        newest_ts = records[0].scraped_at
        latest_batch = [
            r for r in records
            if (newest_ts - r.scraped_at).total_seconds() < 60
        ]

        stores: list[dict[str, Any]] = []
        for r in latest_batch:
            stores.append(
                {
                    "store_name": r.store_name,
                    "store_domain": r.store_domain,
                    "price": r.price,
                    "currency": r.currency,
                    "original_price": r.original_price,
                    "url": r.url,
                    "is_reputable": r.is_reputable,
                    "title": r.title,
                    "condition": r.condition,
                    "shipping": r.shipping,
                }
            )

        stores.sort(key=lambda s: s["price"])

        return {
            "monitor_id": monitor_id,
            "scraped_at": newest_ts.isoformat(),
            "stores": stores,
        }


# ── Private helpers ─────────────────────────────────────────────────────────


def _compute_stats(prices: list[float]) -> dict[str, Any]:
    """Compute summary statistics for a list of prices."""
    if not prices:
        return {
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "std_dev": 0.0,
            "count": 0,
        }

    avg = statistics.mean(prices)
    med = statistics.median(prices)
    std = statistics.pstdev(prices) if len(prices) > 1 else 0.0

    return {
        "avg": round(avg, 2),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "median": round(med, 2),
        "std_dev": round(std, 2),
        "count": len(prices),
    }


def _build_price_history(
    records: list[PriceRecord],
) -> list[dict[str, Any]]:
    """Group price records by date and compute daily aggregates."""
    by_date: dict[str, list[float]] = defaultdict(list)
    for r in records:
        date_key = r.scraped_at.strftime("%Y-%m-%d")
        by_date[date_key].append(r.price)

    history: list[dict[str, Any]] = []
    for date_str in sorted(by_date):
        prices = by_date[date_str]
        history.append(
            {
                "date": date_str,
                "avg_price": round(statistics.mean(prices), 2),
                "min_price": round(min(prices), 2),
                "max_price": round(max(prices), 2),
                "count": len(prices),
            }
        )
    return history


def _build_store_breakdown(
    records: list[PriceRecord],
) -> list[dict[str, Any]]:
    """Group records by store and compute per-store aggregates."""
    store_data: dict[str, dict[str, Any]] = {}

    for r in records:
        key = r.store_domain or r.store_name
        if key not in store_data:
            store_data[key] = {
                "store_name": r.store_name,
                "store_domain": r.store_domain,
                "prices": [],
                "is_reputable": r.is_reputable,
            }
        store_data[key]["prices"].append(r.price)

    breakdown: list[dict[str, Any]] = []
    for info in store_data.values():
        prices = info["prices"]
        # Simple trend: compare first-half avg to second-half avg
        mid = len(prices) // 2
        if mid > 0 and len(prices) > 1:
            first_avg = statistics.mean(prices[:mid])
            second_avg = statistics.mean(prices[mid:])
            if first_avg > 0:
                trend_pct = ((second_avg - first_avg) / first_avg) * 100
            else:
                trend_pct = 0.0
        else:
            trend_pct = 0.0

        if trend_pct < -1:
            trend = "decreasing"
        elif trend_pct > 1:
            trend = "increasing"
        else:
            trend = "stable"

        breakdown.append(
            {
                "store_name": info["store_name"],
                "store_domain": info["store_domain"],
                "current_price": round(prices[-1], 2) if prices else 0.0,
                "avg_price": round(statistics.mean(prices), 2),
                "min_price": round(min(prices), 2),
                "max_price": round(max(prices), 2),
                "is_reputable": info["is_reputable"],
                "price_trend": trend,
                "record_count": len(prices),
            }
        )

    breakdown.sort(key=lambda s: s["current_price"])
    return breakdown


def _build_price_distribution(
    prices: list[float],
    num_buckets: int = 10,
) -> list[dict[str, Any]]:
    """Bucket prices into evenly spaced ranges."""
    if not prices:
        return []

    min_p = min(prices)
    max_p = max(prices)

    if min_p == max_p:
        return [
            {
                "range": f"${min_p:.0f}",
                "range_low": round(min_p, 2),
                "range_high": round(max_p, 2),
                "count": len(prices),
            }
        ]

    bucket_size = (max_p - min_p) / num_buckets
    buckets: list[dict[str, Any]] = []

    for i in range(num_buckets):
        low = min_p + i * bucket_size
        high = min_p + (i + 1) * bucket_size
        count = sum(
            1 for p in prices
            if (low <= p < high) or (i == num_buckets - 1 and p == high)
        )
        buckets.append(
            {
                "range": f"${low:.0f}-${high:.0f}",
                "range_low": round(low, 2),
                "range_high": round(high, 2),
                "count": count,
            }
        )

    return buckets
