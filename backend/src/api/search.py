"""Full-text search API route."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.schemas.sessions import SearchResponse, SearchResult
from src.services import search

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search_sessions(
    q: str,
    source: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SearchResponse:
    """Full-text search across session message chunks."""
    results, total = await search.search_sessions(
        db, user.id, q, source, limit, offset
    )
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        total=total,
        query=q,
    )
