"""API key authentication for external (v1) endpoints.

Keys are configured via the ``API_KEYS`` environment variable as
comma-separated ``name:key`` pairs, e.g.::

    API_KEYS=returnpilot:sk-abc123,other:sk-xyz789

If ``API_KEYS`` is empty or unset, authentication is disabled and all
requests are allowed through (backwards compatible).
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Parse configured keys ────────────────────────────────────────────────────

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

# ── FastAPI dependency ───────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Validate the ``X-API-Key`` header and return the key name.

    If no keys are configured, authentication is skipped and the string
    ``"anonymous"`` is returned.
    """
    # Auth disabled — allow all
    if not _KEY_MAP:
        return "anonymous"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    key_name = _KEY_MAP.get(api_key)
    if key_name is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return key_name
