"""Monitor service -- CRUD and execution of price-monitoring jobs.

Handles creation of monitored products, scheduling scrape runs, persisting
price records, and coordinating alert evaluation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.models import Monitor, PriceRecord, Product
from backend.scraper.google_shopping import GoogleShoppingScraper
from backend.services.alerts import AlertService
from backend.stores.registry import (
    COUNTRY_INFO,
    is_reputable_store,
)

logger = logging.getLogger(__name__)


class MonitorService:
    """Orchestrates product monitors, scrape runs, and price persistence."""

    def __init__(self) -> None:
        self._scraper = GoogleShoppingScraper()
        self._alert_service = AlertService()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_monitor(
        self,
        db: AsyncSession,
        product_name: str,
        query: str,
        countries: list[str],
        interval_minutes: int = 360,
    ) -> Product:
        """Create a product with monitors for each requested country.

        Args:
            db: Async database session.
            product_name: Human-readable product name.
            query: Search query string.
            countries: List of ISO country codes to monitor.
            interval_minutes: Minutes between automatic checks.

        Returns:
            The newly created :class:`Product` with its monitors.
        """
        product = Product(
            name=product_name,
            query=query,
            is_active=True,
        )
        db.add(product)
        await db.flush()

        valid_countries = [
            cc.upper() for cc in countries if cc.upper() in COUNTRY_INFO
        ]
        if not valid_countries:
            valid_countries = settings.default_countries_list

        for cc in valid_countries:
            monitor = Monitor(
                product_id=product.id,
                country_code=cc,
                enabled=True,
                interval_minutes=interval_minutes,
            )
            db.add(monitor)

        await db.flush()
        await db.refresh(product, attribute_names=["monitors"])
        logger.info(
            "Created product id=%d %r with %d monitor(s)",
            product.id,
            product_name,
            len(valid_countries),
        )
        return product

    # ------------------------------------------------------------------
    # Run a check
    # ------------------------------------------------------------------

    async def run_monitor_check(
        self,
        db: AsyncSession,
        monitor_id: int,
    ) -> list[PriceRecord]:
        """Run a single monitor check: scrape, persist prices, check alerts.

        Args:
            db: Async database session.
            monitor_id: PK of the monitor to run.

        Returns:
            List of :class:`PriceRecord` rows created.

        Raises:
            ValueError: If the monitor does not exist.
        """
        stmt = (
            select(Monitor)
            .options(selectinload(Monitor.product))
            .where(Monitor.id == monitor_id)
        )
        result = await db.execute(stmt)
        monitor = result.scalar_one_or_none()
        if monitor is None:
            raise ValueError(f"Monitor {monitor_id} not found")

        query = monitor.product.query
        country = monitor.country_code

        logger.info(
            "Running check for monitor id=%d query=%r country=%s",
            monitor_id,
            query,
            country,
        )

        raw_results = await self._scraper.search(
            query=query,
            country_code=country,
            num_results=50,
        )

        records: list[PriceRecord] = []
        price_dicts: list[dict[str, Any]] = []

        for item in raw_results:
            domain = item.get("store_domain", "")
            reputable = is_reputable_store(domain, country)

            record = PriceRecord(
                monitor_id=monitor_id,
                store_name=item.get("store_name", "Unknown"),
                store_domain=domain,
                price=item["price"],
                currency=item.get("currency", "USD"),
                original_price=item.get("original_price"),
                url=item.get("url", ""),
                title=item.get("title", ""),
                condition=item.get("condition"),
                shipping=item.get("shipping"),
                in_stock=True,
                is_reputable=reputable,
            )
            db.add(record)
            records.append(record)

            price_dicts.append(
                {
                    "price": item["price"],
                    "store_name": item.get("store_name", "Unknown"),
                    "store_domain": domain,
                    "is_reputable": reputable,
                    "in_stock": True,
                }
            )

        # Update last_checked timestamp
        monitor.last_checked = datetime.now(timezone.utc)
        await db.flush()

        # Check alerts with the new price data
        await self._alert_service.check_alerts(db, monitor_id, price_dicts)

        logger.info(
            "Monitor id=%d check complete: %d price records saved",
            monitor_id,
            len(records),
        )
        return records

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_all_monitors(
        self, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get all products with their monitors and latest prices.

        Returns:
            List of product dicts, each containing nested monitors with
            their most recent price records.
        """
        stmt = (
            select(Product)
            .options(
                selectinload(Product.monitors).selectinload(Monitor.price_records),
                selectinload(Product.monitors).selectinload(Monitor.alerts),
            )
            .order_by(Product.created_at.desc())
        )
        result = await db.execute(stmt)
        products = result.scalars().unique().all()

        output: list[dict[str, Any]] = []
        for product in products:
            monitors_data: list[dict[str, Any]] = []
            for monitor in product.monitors:
                # Get only the latest batch of prices (most recent scraped_at)
                latest_prices = sorted(
                    monitor.price_records,
                    key=lambda r: r.scraped_at,
                    reverse=True,
                )
                # Take only the most recent scrape batch
                latest_batch: list[PriceRecord] = []
                if latest_prices:
                    cutoff = latest_prices[0].scraped_at
                    latest_batch = [
                        r for r in latest_prices
                        if (cutoff - r.scraped_at).total_seconds() < 60
                    ]

                monitors_data.append(
                    {
                        "id": monitor.id,
                        "country_code": monitor.country_code,
                        "enabled": monitor.enabled,
                        "interval_minutes": monitor.interval_minutes,
                        "last_checked": (
                            monitor.last_checked.isoformat()
                            if monitor.last_checked
                            else None
                        ),
                        "created_at": monitor.created_at.isoformat(),
                        "alert_count": len(monitor.alerts),
                        "latest_prices": [
                            {
                                "id": r.id,
                                "store_name": r.store_name,
                                "store_domain": r.store_domain,
                                "price": r.price,
                                "currency": r.currency,
                                "original_price": r.original_price,
                                "url": r.url,
                                "title": r.title,
                                "is_reputable": r.is_reputable,
                                "scraped_at": r.scraped_at.isoformat(),
                            }
                            for r in latest_batch[:20]
                        ],
                    }
                )

            output.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "query": product.query,
                    "is_active": product.is_active,
                    "created_at": product.created_at.isoformat(),
                    "updated_at": product.updated_at.isoformat(),
                    "monitors": monitors_data,
                }
            )

        return output

    async def get_product_detail(
        self, db: AsyncSession, product_id: int
    ) -> dict[str, Any] | None:
        """Get a single product with all monitors and latest prices.

        Returns:
            Product dict or ``None`` if not found.
        """
        stmt = (
            select(Product)
            .options(
                selectinload(Product.monitors).selectinload(Monitor.price_records),
                selectinload(Product.monitors).selectinload(Monitor.alerts),
            )
            .where(Product.id == product_id)
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            return None

        # Reuse the same serialisation logic via get_all_monitors format
        monitors_data: list[dict[str, Any]] = []
        for monitor in product.monitors:
            latest_prices = sorted(
                monitor.price_records,
                key=lambda r: r.scraped_at,
                reverse=True,
            )
            monitors_data.append(
                {
                    "id": monitor.id,
                    "country_code": monitor.country_code,
                    "enabled": monitor.enabled,
                    "interval_minutes": monitor.interval_minutes,
                    "last_checked": (
                        monitor.last_checked.isoformat()
                        if monitor.last_checked
                        else None
                    ),
                    "created_at": monitor.created_at.isoformat(),
                    "alert_count": len(monitor.alerts),
                    "alerts": [
                        {
                            "id": a.id,
                            "alert_type": a.alert_type,
                            "threshold_value": a.threshold_value,
                            "is_active": a.is_active,
                            "last_triggered": (
                                a.last_triggered.isoformat()
                                if a.last_triggered
                                else None
                            ),
                            "created_at": a.created_at.isoformat(),
                        }
                        for a in monitor.alerts
                    ],
                    "latest_prices": [
                        {
                            "id": r.id,
                            "store_name": r.store_name,
                            "store_domain": r.store_domain,
                            "price": r.price,
                            "currency": r.currency,
                            "original_price": r.original_price,
                            "url": r.url,
                            "title": r.title,
                            "condition": r.condition,
                            "shipping": r.shipping,
                            "is_reputable": r.is_reputable,
                            "in_stock": r.in_stock,
                            "scraped_at": r.scraped_at.isoformat(),
                        }
                        for r in latest_prices[:50]
                    ],
                }
            )

        return {
            "id": product.id,
            "name": product.name,
            "query": product.query,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
            "monitors": monitors_data,
        }

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def toggle_monitor(
        self,
        db: AsyncSession,
        monitor_id: int,
        enabled: bool,
    ) -> Monitor:
        """Enable or disable a monitor.

        Raises:
            ValueError: If the monitor does not exist.
        """
        stmt = select(Monitor).where(Monitor.id == monitor_id)
        result = await db.execute(stmt)
        monitor = result.scalar_one_or_none()
        if monitor is None:
            raise ValueError(f"Monitor {monitor_id} not found")

        monitor.enabled = enabled
        await db.flush()
        await db.refresh(monitor)
        logger.info(
            "Monitor id=%d toggled enabled=%s", monitor_id, enabled,
        )
        return monitor

    async def add_country_to_product(
        self,
        db: AsyncSession,
        product_id: int,
        country_code: str,
    ) -> Monitor:
        """Add a new country monitor to an existing product.

        Raises:
            ValueError: If the product does not exist or the country is
                already monitored.
        """
        cc = country_code.upper()
        if cc not in COUNTRY_INFO:
            raise ValueError(f"Unsupported country code: {cc}")

        # Ensure product exists
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        # Check for duplicate
        stmt = select(Monitor).where(
            Monitor.product_id == product_id,
            Monitor.country_code == cc,
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise ValueError(
                f"Country {cc} already monitored for product {product_id}"
            )

        monitor = Monitor(
            product_id=product_id,
            country_code=cc,
            enabled=True,
            interval_minutes=settings.SCRAPE_INTERVAL_MINUTES,
        )
        db.add(monitor)
        await db.flush()
        await db.refresh(monitor)
        logger.info(
            "Added country %s to product id=%d", cc, product_id,
        )
        return monitor

    async def remove_country_from_product(
        self,
        db: AsyncSession,
        product_id: int,
        country_code: str,
    ) -> bool:
        """Remove a country monitor from a product.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        cc = country_code.upper()
        stmt = select(Monitor).where(
            Monitor.product_id == product_id,
            Monitor.country_code == cc,
        )
        result = await db.execute(stmt)
        monitor = result.scalar_one_or_none()
        if monitor is None:
            return False

        await db.delete(monitor)
        await db.flush()
        logger.info(
            "Removed country %s from product id=%d", cc, product_id,
        )
        return True

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_product(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> bool:
        """Delete a product and all its monitors, records, and alerts.

        Returns:
            ``True`` if the product existed and was deleted.
        """
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            return False

        await db.delete(product)
        await db.flush()
        logger.info("Deleted product id=%d", product_id)
        return True
