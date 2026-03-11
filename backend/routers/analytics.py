"""Analytics API router -- price statistics, history, and comparisons."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])

_analytics_service = AnalyticsService()


@router.get("/analytics/{monitor_id}")
async def get_price_analytics(
    monitor_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get comprehensive price analytics for a monitor.

    Returns current stats, reputable-only stats, price history,
    store breakdown, and price distribution buckets.
    """
    try:
        return await _analytics_service.get_price_analytics(
            db, monitor_id, days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics/{product_id}/history")
async def get_price_history(
    product_id: int,
    days: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get price history across all countries for a product.

    Returns daily aggregated prices grouped by country.
    """
    try:
        return await _analytics_service.get_price_history(
            db, product_id, days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics/{monitor_id}/compare")
async def compare_store_prices(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compare current prices across stores for a monitor.

    Returns all stores from the latest scrape sorted by price ascending.
    """
    try:
        return await _analytics_service.get_store_comparison(
            db, monitor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
