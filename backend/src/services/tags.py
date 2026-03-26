"""Tag CRUD service — create, list, update, delete tags and session associations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, func, select

from src.models.tag import SessionTag, Tag

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def list_tags(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """List all tags for a user with session_count.

    Returns a list of dicts with tag fields plus ``session_count``.
    """
    stmt = (
        select(
            Tag.id,
            Tag.name,
            Tag.color,
            Tag.created_at,
            func.count(SessionTag.session_id).label("session_count"),
        )
        .outerjoin(SessionTag, SessionTag.tag_id == Tag.id)
        .where(Tag.user_id == user_id)
        .group_by(Tag.id, Tag.name, Tag.color, Tag.created_at)
        .order_by(Tag.name)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "color": row.color,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "session_count": row.session_count,
        }
        for row in rows
    ]


async def create_tag(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    color: str = "#6b7280",
) -> dict:
    """Create a new tag for the user.

    Raises ``ValueError`` if a tag with the same name already exists for this user.
    """
    # Check uniqueness
    existing = await db.execute(select(Tag).where(and_(Tag.user_id == user_id, Tag.name == name)))
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Tag '{name}' already exists")

    tag = Tag(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        color=color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return {
        "id": str(tag.id),
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "session_count": 0,
    }


async def update_tag(
    db: AsyncSession,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    name: str | None = None,
    color: str | None = None,
) -> dict | None:
    """Update a tag's name and/or color.

    Returns ``None`` if the tag does not exist or does not belong to the user.
    Raises ``ValueError`` if renaming to a duplicate name.
    """
    result = await db.execute(select(Tag).where(and_(Tag.id == tag_id, Tag.user_id == user_id)))
    tag = result.scalar_one_or_none()
    if tag is None:
        return None

    if name is not None and name != tag.name:
        # Check uniqueness of the new name
        dup = await db.execute(select(Tag).where(and_(Tag.user_id == user_id, Tag.name == name)))
        if dup.scalar_one_or_none() is not None:
            raise ValueError(f"Tag '{name}' already exists")
        tag.name = name

    if color is not None:
        tag.color = color

    await db.commit()
    await db.refresh(tag)

    # Count sessions for the response
    count_result = await db.execute(
        select(func.count()).select_from(SessionTag).where(SessionTag.tag_id == tag_id)
    )
    session_count = count_result.scalar_one()

    return {
        "id": str(tag.id),
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        "session_count": session_count,
    }


async def delete_tag(
    db: AsyncSession,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> bool:
    """Delete a tag. Returns True if deleted, False if not found."""
    result = await db.execute(select(Tag).where(and_(Tag.id == tag_id, Tag.user_id == user_id)))
    tag = result.scalar_one_or_none()
    if tag is None:
        return False

    await db.delete(tag)
    await db.commit()
    return True


async def add_tag_to_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> bool:
    """Add a tag-session association. Idempotent — returns True on success.

    Returns False if the tag does not belong to the user.
    """
    # Verify ownership
    result = await db.execute(select(Tag).where(and_(Tag.id == tag_id, Tag.user_id == user_id)))
    if result.scalar_one_or_none() is None:
        return False

    # Check if already exists
    existing = await db.execute(
        select(SessionTag).where(
            and_(SessionTag.session_id == session_id, SessionTag.tag_id == tag_id)
        )
    )
    if existing.scalar_one_or_none() is not None:
        return True  # Already associated — idempotent

    assoc = SessionTag(session_id=session_id, tag_id=tag_id)
    db.add(assoc)
    await db.commit()
    return True


async def remove_tag_from_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> bool:
    """Remove a tag-session association. Returns True if removed, False if not found."""
    # Verify ownership
    result = await db.execute(select(Tag).where(and_(Tag.id == tag_id, Tag.user_id == user_id)))
    if result.scalar_one_or_none() is None:
        return False

    del_result = await db.execute(
        delete(SessionTag).where(
            and_(SessionTag.session_id == session_id, SessionTag.tag_id == tag_id)
        )
    )
    await db.commit()
    return del_result.rowcount > 0
