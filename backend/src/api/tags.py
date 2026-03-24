"""Tag CRUD API routes."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.schemas.tags import TagCreate, TagResponse, TagUpdate
from src.services import tags as tag_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[TagResponse]:
    """Return all tags for the authenticated user."""
    items = await tag_service.list_tags(db, user.id)
    return [TagResponse(**item) for item in items]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TagResponse:
    """Create a new tag."""
    try:
        result = await tag_service.create_tag(db, user.id, body.name, body.color)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{body.name}' already exists",
        ) from None
    return TagResponse(**result)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    body: TagUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TagResponse:
    """Update a tag's name and/or color."""
    try:
        result = await tag_service.update_tag(
            db, user.id, tag_id, name=body.name, color=body.color
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{body.name}' already exists",
        ) from None
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return TagResponse(**result)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a tag."""
    deleted = await tag_service.delete_tag(db, user.id, tag_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
