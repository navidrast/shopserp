"""CRUD service for custom store management."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import CustomStore
from backend.stores.registry import register_custom_store, unregister_custom_store

logger = logging.getLogger(__name__)


async def load_into_registry(db: AsyncSession) -> int:
    """Load all active custom stores from the DB into the in-memory registry.

    Returns the number of stores loaded.
    """
    result = await db.execute(
        select(CustomStore).where(CustomStore.is_active.is_(True))
    )
    stores = result.scalars().all()
    count = 0
    for store in stores:
        aliases = [a.strip() for a in (store.aliases or "").split(",") if a.strip()]
        codes = [c.strip() for c in store.country_codes.split(",") if c.strip()]
        register_custom_store(
            name=store.name,
            domain=store.domain,
            aliases=aliases,
            category=store.category,
            tier=store.tier,
            country_codes=codes,
        )
        count += 1
    logger.info("Loaded %d custom stores into registry", count)
    return count


async def create_custom_store(
    db: AsyncSession,
    *,
    name: str,
    domain: str,
    aliases: list[str] | None = None,
    category: str = "marketplace",
    tier: int = 2,
    country_codes: list[str] | None = None,
) -> CustomStore:
    """Create a new custom store and register it in-memory."""
    domain_clean = domain.lower().removeprefix("www.")
    codes = country_codes or ["US"]

    store = CustomStore(
        name=name,
        domain=domain_clean,
        aliases=",".join(aliases) if aliases else None,
        category=category,
        tier=tier,
        country_codes=",".join(c.upper() for c in codes),
    )
    db.add(store)
    await db.flush()

    register_custom_store(
        name=name,
        domain=domain_clean,
        aliases=aliases,
        category=category,
        tier=tier,
        country_codes=codes,
    )
    logger.info("Created custom store %r (%s)", name, domain_clean)
    return store


async def list_custom_stores(db: AsyncSession) -> list[CustomStore]:
    """Return all custom stores."""
    result = await db.execute(
        select(CustomStore).order_by(CustomStore.name)
    )
    return list(result.scalars().all())


async def delete_custom_store(db: AsyncSession, store_id: int) -> bool:
    """Delete a custom store by ID. Returns True if found and deleted."""
    result = await db.execute(
        select(CustomStore).where(CustomStore.id == store_id)
    )
    store = result.scalar_one_or_none()
    if store is None:
        return False

    unregister_custom_store(store.domain)
    await db.delete(store)
    await db.flush()
    logger.info("Deleted custom store %r (%s)", store.name, store.domain)
    return True
