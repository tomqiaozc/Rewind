"""API key management routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Body, Depends

from src.auth.api_key import create_api_key
from src.auth.dependencies import get_current_user
from src.db.session import get_db

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
