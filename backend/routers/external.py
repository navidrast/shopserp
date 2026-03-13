"""External API router — /api/v1/ endpoints for ReturnPilot and other consumers.

All endpoints require a valid ``X-API-Key`` header (unless auth is disabled).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_api_key
from backend.database import get_db
from backend.schemas import (
    CustomStoreCreate,
    CustomStoreResponse,
    ExtendedSearchRequest,
    SearchResponse,
    StoreReputationResponse,
    CountrySearchResults,
    SearchResultItem,
)
from backend.services.search import SearchService
from backend.services.monitor import MonitorService
from backend.services.analytics import AnalyticsService
from backend.services import custom_stores as custom_store_service
from backend.stores.registry import (
    COUNTRY_INFO,
    get_stores_for_country,
    get_supported_countries,
    is_reputable_store,
    is_reputable_store_by_name,
    identify_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["external-v1"],
    dependencies=[Depends(require_api_key)],
)

_search_service = SearchService()
_monitor_service = MonitorService()
_analytics_service = AnalyticsService()


# ── Search ────────────────────────────────────────────────────────────────────


@router.post("/search", response_model=SearchResponse)
async def search(
    body: ExtendedSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search Google Shopping with structured product identifiers.

    Supports UPC/EAN, manufacturer part number, brand/model filtering,
    and condition filtering. Falls back through identifiers in priority
    order: UPC → MPN → brand+model → free-text query.
    """
    has_structured = any([body.upc, body.part_number, body.brand, body.model])

    try:
        if has_structured:
            grouped = await _search_service.structured_search(
                db=db,
                query=body.query,
                upc=body.upc,
                part_number=body.part_number,
                sku=body.sku,
                brand=body.brand,
                model=body.model,
                condition=body.condition,
                countries=body.countries,
                max_results=body.max_results,
            )
        else:
            # Plain text search (original behavior)
            if not body.query:
                raise HTTPException(
                    status_code=400,
                    detail="Provide 'query' or structured identifiers (upc, part_number, brand, model)",
                )
            grouped = await _search_service.search(
                db=db,
                query=body.query,
                countries=body.countries,
                max_results=body.max_results,
            )
            # Apply condition filter even for plain text search
            if body.condition and body.condition != "any":
                grouped = {
                    cc: _search_service.filter_results(items, condition=body.condition)
                    for cc, items in grouped.items()
                }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("v1 search failed")
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc

    # Build the effective query string for the response
    effective_query = body.query or body.upc or body.part_number or ""
    if body.brand and body.model:
        effective_query = f"{body.brand} {body.model}"
    elif body.brand:
        effective_query = body.brand
    elif body.model:
        effective_query = body.model

    country_results: list[CountrySearchResults] = []
    total = 0

    for cc, items in grouped.items():
        info = COUNTRY_INFO.get(cc, {})
        result_items = [
            SearchResultItem(
                store_name=r.get("store_name", "Unknown"),
                store_domain=r.get("store_domain", ""),
                price=r["price"],
                currency=r.get("currency", "USD"),
                original_price=r.get("original_price"),
                url=r.get("url") or r.get("store_link") or r.get("product_link") or "",
                title=r.get("title", ""),
                condition=r.get("condition"),
                shipping=r.get("shipping"),
                in_stock=r.get("in_stock", True),
                is_reputable=r.get("is_reputable", False),
                image_url=r.get("image_url"),
                rating=r.get("rating"),
                review_count=r.get("review_count"),
            )
            for r in items
            if r.get("price") is not None
        ]
        country_results.append(
            CountrySearchResults(
                country_code=cc,
                country_name=info.get("name", cc),
                currency=info.get("currency", "USD"),
                results=result_items,
                result_count=len(result_items),
            )
        )
        total += len(result_items)

    return SearchResponse(
        query=effective_query,
        countries=country_results,
        total_results=total,
    )


# ── Store reputation ──────────────────────────────────────────────────────────


@router.get("/stores/check", response_model=StoreReputationResponse)
async def check_store_reputation(
    domain: str | None = Query(default=None),
    name: str | None = Query(default=None),
    country_code: str = Query(default="US"),
) -> StoreReputationResponse:
    """Check whether a domain or store name is reputable."""
    cc = country_code.upper()

    if domain:
        reputable = is_reputable_store(domain, cc)
        store_name_found, _ = identify_store(domain)
        return StoreReputationResponse(
            domain=domain,
            country_code=cc,
            is_reputable=reputable,
            store_name=store_name_found if reputable else None,
        )

    if name:
        reputable = is_reputable_store_by_name(name, cc)
        return StoreReputationResponse(
            name=name,
            country_code=cc,
            is_reputable=reputable,
            store_name=name if reputable else None,
        )

    raise HTTPException(status_code=400, detail="Provide 'domain' or 'name' query parameter")


@router.get("/stores/{country_code}")
async def list_stores(country_code: str) -> dict[str, Any]:
    """List reputable stores for a country."""
    cc = country_code.upper()
    info = COUNTRY_INFO.get(cc)
    stores = get_stores_for_country(cc)
    return {
        "country_code": cc,
        "country_name": info["name"] if info else cc,
        "stores": [
            {"name": s.name, "domain": s.domain, "category": s.category, "tier": s.tier}
            for s in stores
        ],
    }


# ── Custom stores ─────────────────────────────────────────────────────────────


@router.post("/stores/custom", response_model=CustomStoreResponse, status_code=201)
async def create_custom_store(
    body: CustomStoreCreate,
    db: AsyncSession = Depends(get_db),
) -> CustomStoreResponse:
    """Add a custom store to the reputable registry."""
    try:
        store = await custom_store_service.create_custom_store(
            db,
            name=body.name,
            domain=body.domain,
            aliases=body.aliases or None,
            category=body.category,
            tier=body.tier,
            country_codes=body.country_codes or None,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CustomStoreResponse.model_validate(store)


@router.get("/stores/custom", response_model=list[CustomStoreResponse])
async def list_custom_stores(
    db: AsyncSession = Depends(get_db),
) -> list[CustomStoreResponse]:
    """List all custom stores."""
    stores = await custom_store_service.list_custom_stores(db)
    return [CustomStoreResponse.model_validate(s) for s in stores]


@router.delete("/stores/custom/{store_id}", status_code=204, response_model=None)
async def delete_custom_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a custom store."""
    deleted = await custom_store_service.delete_custom_store(db, store_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom store not found")
    return Response(status_code=204)


# ── Monitors ──────────────────────────────────────────────────────────────────


class _CreateMonitorV1(BaseModel):
    """Monitor creation request for v1 API."""
    name: str
    query: str
    countries: list[str] = Field(default_factory=lambda: ["US"])
    max_results: int = Field(default=30, ge=1, le=100)
    interval_minutes: int = 360


@router.post("/monitors", status_code=201)
async def create_monitor(
    body: _CreateMonitorV1,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new monitored product."""
    product = await _monitor_service.create_monitor(
        db=db,
        product_name=body.name,
        query=body.query,
        countries=body.countries,
        interval_minutes=body.interval_minutes,
    )
    return {
        "id": product.id,
        "name": product.name,
        "query": product.query,
        "is_active": product.is_active,
        "monitors": [
            {
                "id": m.id,
                "country_code": m.country_code,
                "enabled": m.enabled,
                "interval_minutes": m.interval_minutes,
            }
            for m in product.monitors
        ],
    }


@router.get("/monitors")
async def list_monitors(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all monitored products."""
    return await _monitor_service.get_all_monitors(db)


@router.get("/monitors/{product_id}")
async def get_monitor(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get monitor detail for a product."""
    result = await _monitor_service.get_product_detail(db, product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/monitors/{product_id}", status_code=204, response_model=None)
async def delete_monitor(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a monitored product."""
    deleted = await _monitor_service.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return Response(status_code=204)


@router.post("/monitors/{monitor_id}/check")
async def trigger_check(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an immediate price check for a monitor."""
    try:
        records = await _monitor_service.run_monitor_check(db, monitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("v1 manual check failed for monitor=%d", monitor_id)
        raise HTTPException(status_code=502, detail=f"Scrape failed: {exc}") from exc

    return {
        "monitor_id": monitor_id,
        "records_created": len(records),
        "prices": [
            {
                "store_name": r.store_name,
                "price": r.price,
                "currency": r.currency,
                "is_reputable": r.is_reputable,
            }
            for r in records[:20]
        ],
    }


# ── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/analytics/{monitor_id}")
async def get_analytics(
    monitor_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get price analytics for a monitor."""
    try:
        return await _analytics_service.get_price_analytics(db, monitor_id, days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics/{product_id}/history")
async def get_price_history(
    product_id: int,
    days: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get price history across all countries for a product."""
    try:
        return await _analytics_service.get_price_history(db, product_id, days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics/{monitor_id}/compare")
async def compare_stores(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compare current prices across stores for a monitor."""
    try:
        return await _analytics_service.get_store_comparison(db, monitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Countries ─────────────────────────────────────────────────────────────────


@router.get("/countries")
async def list_countries() -> list[dict[str, Any]]:
    """List all supported countries."""
    return get_supported_countries()
