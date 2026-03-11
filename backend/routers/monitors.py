"""Monitors API router -- CRUD for products, monitors, and alerts."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.alerts import AlertService
from backend.services.monitor import MonitorService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["monitors"])

_monitor_service = MonitorService()
_alert_service = AlertService()


# ── Request schemas (router-local) ──────────────────────────────────────────


class CreateMonitorRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    query: str = Field(..., min_length=1, max_length=1024)
    countries: list[str] = Field(default_factory=lambda: ["US"])
    interval_minutes: int = Field(default=360, ge=5, le=44640)


class ToggleRequest(BaseModel):
    enabled: bool


class AddCountryRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")


class CreateAlertRequest(BaseModel):
    alert_type: str = Field(..., pattern=r"^(below_threshold|price_drop|back_in_stock)$")
    threshold_value: float | None = None


# ── Product / Monitor endpoints ─────────────────────────────────────────────


@router.get("/monitors")
async def list_monitors(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all products with their monitors and latest prices."""
    return await _monitor_service.get_all_monitors(db)


@router.post("/monitors", status_code=201)
async def create_monitor(
    body: CreateMonitorRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new monitored product with monitors for each country."""
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


@router.get("/monitors/{product_id}")
async def get_product_detail(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a product with all monitors, alerts, and latest prices."""
    result = await _monitor_service.get_product_detail(db, product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/monitors/{product_id}", status_code=204, response_model=None)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a product and all associated monitors, records, and alerts."""
    deleted = await _monitor_service.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")


# ── Monitor toggle ──────────────────────────────────────────────────────────


@router.patch("/monitors/{monitor_id}/toggle")
async def toggle_monitor(
    monitor_id: int,
    body: ToggleRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enable or disable a monitor."""
    try:
        monitor = await _monitor_service.toggle_monitor(
            db, monitor_id, body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "id": monitor.id,
        "enabled": monitor.enabled,
        "country_code": monitor.country_code,
    }


# ── Country management ──────────────────────────────────────────────────────


@router.post("/monitors/{product_id}/countries", status_code=201)
async def add_country(
    product_id: int,
    body: AddCountryRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a new country monitor to a product."""
    try:
        monitor = await _monitor_service.add_country_to_product(
            db, product_id, body.country_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": monitor.id,
        "product_id": product_id,
        "country_code": monitor.country_code,
        "enabled": monitor.enabled,
    }


@router.delete(
    "/monitors/{product_id}/countries/{country_code}",
    status_code=204,
    response_model=None,
)
async def remove_country(
    product_id: int,
    country_code: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a country monitor from a product."""
    removed = await _monitor_service.remove_country_from_product(
        db, product_id, country_code.upper(),
    )
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Country {country_code.upper()} not found for product {product_id}",
        )


# ── Manual check ────────────────────────────────────────────────────────────


@router.post("/monitors/{monitor_id}/check")
async def trigger_check(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an immediate scrape check for a monitor."""
    try:
        records = await _monitor_service.run_monitor_check(db, monitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Manual check failed for monitor=%d", monitor_id)
        raise HTTPException(
            status_code=502, detail=f"Scrape failed: {exc}",
        ) from exc

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


# ── Alerts ──────────────────────────────────────────────────────────────────


@router.post("/monitors/{monitor_id}/alerts", status_code=201)
async def create_alert(
    monitor_id: int,
    body: CreateAlertRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a price alert for a monitor."""
    try:
        alert = await _alert_service.create_alert(
            db=db,
            monitor_id=monitor_id,
            alert_type=body.alert_type,
            threshold=body.threshold_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": alert.id,
        "monitor_id": alert.monitor_id,
        "alert_type": alert.alert_type,
        "threshold_value": alert.threshold_value,
        "is_active": alert.is_active,
    }


@router.get("/monitors/{monitor_id}/alerts")
async def list_alerts(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all alerts for a monitor."""
    alerts = await _alert_service.get_alerts_for_monitor(db, monitor_id)
    return [
        {
            "id": a.id,
            "monitor_id": a.monitor_id,
            "alert_type": a.alert_type,
            "threshold_value": a.threshold_value,
            "is_active": a.is_active,
            "last_triggered": (
                a.last_triggered.isoformat() if a.last_triggered else None
            ),
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.delete("/monitors/alerts/{alert_id}", status_code=204, response_model=None)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a price alert."""
    deleted = await _alert_service.delete_alert(db, alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
