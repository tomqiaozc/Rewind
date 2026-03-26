"""FastAPI authentication dependencies.

Two auth paths are supported:

1. **API key** — ``Authorization: Bearer rw_...`` header.  The key is
   SHA-256 hashed and looked up in the ``api_keys`` table.
2. **BFF proxy** — ``X-Backend-Secret`` + ``X-User-Id`` headers set by
   the Next.js backend-for-frontend proxy after validating the NextAuth
   session.

If neither path matches, a 401 Unauthorized response is returned.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.auth.api_key import hash_api_key
from src.config import settings
from src.db.session import get_db
from src.models.base import ApiKey, User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """Resolve the authenticated user from the request.

    Raises :class:`~fastapi.HTTPException` with status 401 when the
    request cannot be authenticated.
    """

    # ----- Path 1: API key (Bearer rw_...) ----- #
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer rw_"):
        api_key_value = auth_header[len("Bearer ") :]
        key_hash = hash_api_key(api_key_value)
        result = await db.execute(
            select(ApiKey).options(selectinload(ApiKey.user)).where(ApiKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()
        if api_key is None or api_key.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Update last_used_at
        api_key.last_used_at = datetime.utcnow()
        await db.commit()
        return api_key.user

    # ----- Path 2: BFF proxy (X-Backend-Secret + X-User-Id) ----- #
    backend_secret = request.headers.get("X-Backend-Secret")
    user_id_header = request.headers.get("X-User-Id")

    if backend_secret and user_id_header:
        if backend_secret != settings.backend_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid backend secret",
            )

        try:
            user_uuid = uuid.UUID(user_id_header)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format",
            ) from exc

        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    # ----- No auth provided ----- #
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
