"""API key management router.

Provides CRUD endpoints for managing API keys used by external
integrations. These endpoints are NOT authenticated themselves -- the
ShopSerp UI is protected by Cloudflare Access at the network layer.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend.database import async_session_factory
from backend.models import ApiKey
from backend.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["api-keys"])


def _generate_key() -> str:
    """Generate a new API key in the format ``sk-<32 hex chars>``."""
    return "sk-" + secrets.token_hex(16)


def _hash_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest of *raw_key*."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(payload: ApiKeyCreate) -> ApiKeyCreatedResponse:
    """Generate a new API key.

    The full key is returned **only once** in the response.  Store it
    securely -- it cannot be retrieved later.
    """
    raw_key = _generate_key()
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:8]

    async with async_session_factory() as session:
        api_key = ApiKey(
            name=payload.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=True,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        logger.info("Created API key %r (id=%d)", payload.name, api_key.id)

        return ApiKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,
            key_prefix=key_prefix,
            created_at=api_key.created_at,
        )


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys() -> list[ApiKeyResponse]:
    """List all API keys (metadata only, never the full key)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ApiKey).order_by(ApiKey.created_at.desc())
        )
        keys = result.scalars().all()
        return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(key_id: int) -> None:
    """Permanently revoke and delete an API key."""
    async with async_session_factory() as session:
        api_key = await session.get(ApiKey, key_id)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )
        await session.delete(api_key)
        await session.commit()
        logger.info("Deleted API key id=%d name=%r", key_id, api_key.name)


@router.patch("/keys/{key_id}", response_model=ApiKeyResponse)
async def toggle_api_key(key_id: int) -> ApiKeyResponse:
    """Toggle an API key between active and inactive."""
    async with async_session_factory() as session:
        api_key = await session.get(ApiKey, key_id)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )
        api_key.is_active = not api_key.is_active
        await session.commit()
        await session.refresh(api_key)
        logger.info(
            "Toggled API key id=%d name=%r active=%s",
            key_id, api_key.name, api_key.is_active,
        )
        return ApiKeyResponse.model_validate(api_key)
