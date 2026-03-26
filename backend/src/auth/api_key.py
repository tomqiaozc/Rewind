"""API key generation, hashing, and verification."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.base import ApiKey, User

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


def generate_api_key() -> str:
    """Generate a new API key with the ``rw_`` prefix.

    Returns a string of the form ``rw_<32 hex chars>``.
    """
    return "rw_" + secrets.token_hex(16)


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of *key*."""
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    user_id: UUID,
    device_name: str | None = None,
) -> tuple[str, ApiKey]:
    """Create a new API key for the given user.

    Returns ``(plaintext_key, api_key_record)``.  The plaintext key is
    shown to the user exactly once; only the hash is persisted.
    """
    plaintext = generate_api_key()
    key_hash = hash_api_key(plaintext)

    api_key = ApiKey(
        user_id=user_id,
        key_hash=key_hash,
        device_name=device_name,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return plaintext, api_key


async def verify_api_key(db: AsyncSession, key: str) -> User | None:
    """Verify an API key and return the associated user, or ``None``.

    On success the key's ``last_used_at`` timestamp is updated.
    """
    key_hash = hash_api_key(key)
    result = await db.execute(
        select(ApiKey).options(selectinload(ApiKey.user)).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return None

    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    await db.commit()
    return api_key.user
