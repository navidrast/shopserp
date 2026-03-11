"""Alert service -- creates, checks, and fires price alerts.

Supports three alert types:
- ``below_threshold``: fires when any price drops below a configured value.
- ``price_drop``: fires when the average price drops >10 % compared to the
  previous check.
- ``back_in_stock``: fires when a previously out-of-stock item reappears.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import PriceAlert, PriceRecord

logger = logging.getLogger(__name__)

_PRICE_DROP_THRESHOLD_PCT = 0.10  # 10 % drop triggers an alert


class AlertService:
    """Manage and evaluate price alerts for monitors."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_alert(
        self,
        db: AsyncSession,
        monitor_id: int,
        alert_type: str,
        threshold: float | None = None,
    ) -> PriceAlert:
        """Create a new price alert for a monitor.

        Args:
            db: Async database session.
            monitor_id: FK to the monitor.
            alert_type: One of ``below_threshold``, ``price_drop``,
                ``back_in_stock``.
            threshold: Price threshold (required for ``below_threshold``).

        Returns:
            The newly created :class:`PriceAlert` instance.

        Raises:
            ValueError: If ``alert_type`` is ``below_threshold`` and no
                threshold is provided, or if the type is unknown.
        """
        valid_types = {"below_threshold", "price_drop", "back_in_stock"}
        if alert_type not in valid_types:
            raise ValueError(
                f"Invalid alert_type {alert_type!r}. "
                f"Must be one of {valid_types}."
            )
        if alert_type == "below_threshold" and threshold is None:
            raise ValueError(
                "threshold is required for 'below_threshold' alerts."
            )

        alert = PriceAlert(
            monitor_id=monitor_id,
            alert_type=alert_type,
            threshold_value=threshold,
            is_active=True,
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)
        logger.info(
            "Created alert id=%d type=%s monitor=%d",
            alert.id,
            alert_type,
            monitor_id,
        )
        return alert

    async def get_alerts_for_monitor(
        self, db: AsyncSession, monitor_id: int
    ) -> list[PriceAlert]:
        """Return all alerts for a monitor."""
        stmt = (
            select(PriceAlert)
            .where(PriceAlert.monitor_id == monitor_id)
            .order_by(PriceAlert.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_alert(self, db: AsyncSession, alert_id: int) -> bool:
        """Delete an alert by ID.

        Returns:
            ``True`` if the alert was found and deleted, ``False`` otherwise.
        """
        stmt = select(PriceAlert).where(PriceAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            return False
        await db.delete(alert)
        await db.flush()
        logger.info("Deleted alert id=%d", alert_id)
        return True

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    async def check_alerts(
        self,
        db: AsyncSession,
        monitor_id: int,
        prices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Evaluate all active alerts for a monitor against new prices.

        Args:
            db: Async database session.
            monitor_id: The monitor whose alerts to check.
            prices: List of price dicts from the latest scrape.  Each dict
                should contain at least ``price``, ``store_name``, and
                ``in_stock`` keys.

        Returns:
            List of triggered-alert info dicts (may be empty).
        """
        stmt = (
            select(PriceAlert)
            .where(
                PriceAlert.monitor_id == monitor_id,
                PriceAlert.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        alerts = list(result.scalars().all())

        if not alerts or not prices:
            return []

        triggered: list[dict[str, Any]] = []

        for alert in alerts:
            fire_data = await self._evaluate_alert(db, alert, prices)
            if fire_data is not None:
                alert.last_triggered = datetime.now(timezone.utc)
                triggered.append(fire_data)

                # Fire webhook asynchronously (best-effort)
                await self.send_webhook(alert, fire_data)

        if triggered:
            await db.flush()
            logger.info(
                "Triggered %d alert(s) for monitor=%d",
                len(triggered),
                monitor_id,
            )

        return triggered

    async def _evaluate_alert(
        self,
        db: AsyncSession,
        alert: PriceAlert,
        prices: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Evaluate a single alert against the latest prices.

        Returns a notification payload dict if triggered, else ``None``.
        """
        if alert.alert_type == "below_threshold":
            return self._check_below_threshold(alert, prices)

        if alert.alert_type == "price_drop":
            return await self._check_price_drop(db, alert, prices)

        if alert.alert_type == "back_in_stock":
            return await self._check_back_in_stock(db, alert, prices)

        return None

    # -- below_threshold ------------------------------------------------

    @staticmethod
    def _check_below_threshold(
        alert: PriceAlert,
        prices: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        threshold = alert.threshold_value
        if threshold is None:
            return None

        matches = [
            p for p in prices
            if p.get("price") is not None and p["price"] < threshold
        ]
        if not matches:
            return None

        best = min(matches, key=lambda p: p["price"])
        return {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "message": (
                f"Price dropped below {threshold}: "
                f"{best['price']} at {best.get('store_name', 'Unknown')}"
            ),
            "price": best["price"],
            "store": best.get("store_name", "Unknown"),
            "threshold": threshold,
        }

    # -- price_drop -----------------------------------------------------

    async def _check_price_drop(
        self,
        db: AsyncSession,
        alert: PriceAlert,
        prices: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        current_prices = [
            p["price"] for p in prices if p.get("price") is not None
        ]
        if not current_prices:
            return None
        current_avg = sum(current_prices) / len(current_prices)

        # Fetch previous check's average
        stmt = (
            select(PriceRecord.price)
            .where(PriceRecord.monitor_id == alert.monitor_id)
            .order_by(PriceRecord.scraped_at.desc())
            .limit(200)
        )
        result = await db.execute(stmt)
        previous = [row[0] for row in result.all()]
        if not previous:
            return None

        prev_avg = sum(previous) / len(previous)
        if prev_avg <= 0:
            return None

        drop_pct = (prev_avg - current_avg) / prev_avg
        if drop_pct < _PRICE_DROP_THRESHOLD_PCT:
            return None

        return {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "message": (
                f"Average price dropped {drop_pct:.1%}: "
                f"from {prev_avg:.2f} to {current_avg:.2f}"
            ),
            "previous_avg": round(prev_avg, 2),
            "current_avg": round(current_avg, 2),
            "drop_percent": round(drop_pct * 100, 1),
        }

    # -- back_in_stock --------------------------------------------------

    async def _check_back_in_stock(
        self,
        db: AsyncSession,
        alert: PriceAlert,
        prices: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        in_stock_now = [p for p in prices if p.get("in_stock", True)]
        if not in_stock_now:
            return None

        # Check if there were zero results previously (proxy for out-of-stock)
        stmt = (
            select(PriceRecord)
            .where(PriceRecord.monitor_id == alert.monitor_id)
            .order_by(PriceRecord.scraped_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_record = result.scalar_one_or_none()

        # If there was no previous record or the last one was out of stock
        if last_record is None or not last_record.in_stock:
            best = min(in_stock_now, key=lambda p: p.get("price", float("inf")))
            return {
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "message": (
                    f"Back in stock at {best.get('store_name', 'Unknown')} "
                    f"for {best.get('price', 'N/A')}"
                ),
                "price": best.get("price"),
                "store": best.get("store_name", "Unknown"),
            }

        return None

    # ------------------------------------------------------------------
    # Webhook notifications
    # ------------------------------------------------------------------

    async def send_webhook(
        self,
        alert: PriceAlert,
        price_data: dict[str, Any],
    ) -> None:
        """Send a notification payload to the configured webhook URL.

        The payload is formatted to be compatible with both Discord and
        Slack incoming webhooks.

        Args:
            alert: The triggered alert.
            price_data: Notification payload dict.
        """
        webhook_url = settings.ALERT_WEBHOOK_URL
        if not webhook_url:
            logger.debug("No webhook URL configured; skipping notification.")
            return

        # Build a Discord / Slack compatible payload
        payload: dict[str, Any] = {
            # Slack field
            "text": price_data.get("message", "Price alert triggered"),
            # Discord field
            "content": price_data.get("message", "Price alert triggered"),
            "embeds": [
                {
                    "title": f"ShopSerp Alert: {alert.alert_type}",
                    "description": price_data.get("message", ""),
                    "color": 3066993,  # green
                    "fields": [
                        {
                            "name": k,
                            "value": str(v),
                            "inline": True,
                        }
                        for k, v in price_data.items()
                        if k not in {"alert_id", "alert_type", "message"}
                    ],
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
            logger.info(
                "Webhook sent for alert id=%d (HTTP %d)",
                alert.id,
                resp.status_code,
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Webhook returned HTTP %d for alert id=%d",
                exc.response.status_code,
                alert.id,
            )
        except httpx.RequestError as exc:
            logger.error(
                "Webhook request failed for alert id=%d: %s",
                alert.id,
                exc,
            )
