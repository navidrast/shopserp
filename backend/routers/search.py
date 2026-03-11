"""Search API router -- POST /api/search."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import SearchRequest, SearchResponse, CountrySearchResults, SearchResultItem
from backend.services.search import SearchService
from backend.stores.registry import COUNTRY_INFO

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])

_search_service = SearchService()


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search Google Shopping across one or more countries.

    Returns results grouped by country with reputable-store tagging.
    """
    try:
        grouped = await _search_service.search(
            db=db,
            query=body.query,
            countries=body.countries,
            max_results=body.max_results,
        )
    except Exception as exc:
        logger.exception("Search failed for query=%r", body.query)
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc

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
                url=r.get("url", ""),
                title=r.get("title", ""),
                condition=r.get("condition"),
                shipping=r.get("shipping"),
                in_stock=r.get("in_stock", True),
                is_reputable=r.get("is_reputable", False),
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
        query=body.query,
        countries=country_results,
        total_results=total,
    )
