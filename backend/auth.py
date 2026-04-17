"""API key authentication for external (v1) endpoints.

Keys are validated from two sources:

1. **Environment variable** -- ``API_KEYS`` as comma-separated
   ``name:key`` pairs (unchanged legacy behaviour).
2. **Database** -- ``api_keys`` table with SHA-256 hashed keys.
   DB results are cached in memory for 60 seconds.

If *neither* source has any keys configured, authentication is disabled
and all requests are allowed through as ``"anonymous"``.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Parse configured env-var keys ───────────────────────────────────────────

_KEY_MAP: dict[str, str] = {}  # key_value -> key_name


def _parse_api_keys() -> None:
    """Populate *_KEY_MAP* from the ``API_KEYS`` setting."""
    _KEY_MAP.clear()
    raw = settings.API_KEYS
    if not raw:
        return
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            logger.warning("Ignoring malformed API_KEYS entry (no colon): %r", pair)
            continue
        name, key = pair.split(":", 1)
        name, key = name.strip(), key.strip()
        if name and key:
            _KEY_MAP[key] = name
            logger.info("Registered API key for %r", name)


_parse_api_keys()

# ── DB key cache ────────────────────────────────────────────────────────────

_DB_KEY_CACHE: dict[str, tuple[str, int]] = {}  # key_hash -> (key_name, key_id)
_DB_CACHE_TS: float = 0.0
_DB_CACHE_TTL: float = 60.0  # seconds


async def _refresh_db_cache() -> None:
    """Reload active API key hashes from the database."""
    global _DB_KEY_CACHE, _DB_CACHE_TS

    try:
        from backend.database import async_session_factory
        from backend.models import ApiKey

        async with async_session_factory() as session:
            result = await session.execute(
                select(ApiKey.key_hash, ApiKey.name, ApiKey.id).where(
                    ApiKey.is_active == True  # noqa: E712
                )
            )
            rows = result.all()
            _DB_KEY_CACHE = {row.key_hash: (row.name, row.id) for row in rows}
            _DB_CACHE_TS = time.monotonic()
    except Exception:
        logger.exception("Failed to refresh DB API key cache")


async def _get_db_cache() -> dict[str, tuple[str, int]]:
    """Return the DB key cache, refreshing if stale."""
    if time.monotonic() - _DB_CACHE_TS > _DB_CACHE_TTL:
        await _refresh_db_cache()
    return _DB_KEY_CACHE


async def _update_last_used(key_id: int) -> None:
    """Update the ``last_used_at`` timestamp for a DB key (fire-and-forget)."""
    try:
        from backend.database import async_session_factory
        from backend.models import ApiKey

        async with async_session_factory() as session:
            await session.execute(
                update(ApiKey)
                .where(ApiKey.id == key_id)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception:
        logger.debug("Failed to update last_used_at for key id=%d", key_id, exc_info=True)


# ── FastAPI dependency ──────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Validate the ``X-API-Key`` header and return the key name.

    Checks env-var keys first, then DB keys.  If no keys are configured
    in either source, authentication is skipped and ``"anonymous"`` is
    returned.
    """
    db_cache = await _get_db_cache()

    # Auth disabled -- no keys in env or DB
    if not _KEY_MAP and not db_cache:
        return "anonymous"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    # Check env-var keys first (fast path)
    key_name = _KEY_MAP.get(api_key)
    if key_name is not None:
        return key_name

    # Check DB keys
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    hit = db_cache.get(key_hash)
    if hit is not None:
        key_name, key_id = hit
        # Update last_used_at in background (best-effort)
        import asyncio
        asyncio.create_task(_update_last_used(key_id))
        return key_name

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
