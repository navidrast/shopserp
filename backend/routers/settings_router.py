"""Settings API router -- countries, stores, and health check."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from backend.schemas import HealthResponse
from backend.stores.registry import (
    COUNTRY_INFO,
    get_stores_for_country,
    get_supported_countries,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])


@router.get("/countries")
async def list_countries() -> list[dict[str, Any]]:
    """List all supported countries with their store counts.

    Returns a sorted list of country objects including code, name,
    currency, and the number of registered reputable stores.
    """
    result = get_supported_countries()
    # get_supported_countries returns list[dict] with code/name/currency/stores_count
    return result


@router.get("/countries/{code}/stores")
async def list_stores_for_country(code: str) -> dict[str, Any]:
    """List all registered reputable stores for a specific country.

    Args:
        code: ISO 3166-1 alpha-2 country code (e.g. ``US``, ``AU``).
    """
    cc = code.upper()
    info = COUNTRY_INFO.get(cc)
    if info is None:
        return {
            "country_code": cc,
            "country_name": "Unknown",
            "stores": [],
        }

    stores = get_stores_for_country(cc)
    return {
        "country_code": cc,
        "country_name": info.get("name", cc),
        "currency": info.get("currency", ""),
        "stores": [
            {
                "name": s.name,
                "domain": s.domain,
                "category": s.category,
                "tier": s.tier,
            }
            for s in stores
        ],
    }


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Application health check endpoint."""
    return HealthResponse()
