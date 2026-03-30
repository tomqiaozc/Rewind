"""API key management routes."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy import select

from src.auth.api_key import create_api_key
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import ApiKey
from src.schemas.keys import ApiKeyResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.post("")
async def create_key(
    device_name: Optional[str] = Body(None, embed=True),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Create a new API key for the authenticated user.

    The plaintext key is returned exactly once in the response.
    """
    plaintext, api_key = await create_api_key(db, user.id, device_name)
    return {
        "key": plaintext,
        "id": str(api_key.id),
        "device_name": api_key.device_name,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[dict]:
    """List all API keys for the authenticated user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": str(k.id),
            "device_name": k.device_name,
            "key_prefix": k.key_prefix,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Delete an API key owned by the authenticated user."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    await db.delete(api_key)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
