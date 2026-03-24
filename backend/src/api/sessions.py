"""Session read API routes — list, detail, filters, and raw content."""
from __future__ import annotations

import gzip
import json
import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.auth.dependencies import get_current_user
from src.config import settings
from src.db.session import get_db
from src.models.tag import SessionTag, Tag
from src.schemas.sessions import (
    BatchRequest,
    BatchResponse,
    FilterValues,
    MessageDetail,
    SessionDetail,
    SessionListItem,
    SessionListResponse,
    StarRequest,
    TagSummary,
)
from src.services import sessions
from src.services.storage import BlobStorageService
from src.services.tags import add_tag_to_session, remove_tag_from_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    source: Optional[str] = None,
    project: Optional[str] = None,
    model: Optional[str] = None,
    is_starred: Optional[bool] = None,
    sort_by: str = "last_message_at",
    sort_order: str = "desc",
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SessionListResponse:
    """Return a paginated list of sessions for the authenticated user."""
    items, total = await sessions.list_sessions(
        db,
        user.id,
        page=page,
        page_size=page_size,
        source=source,
        project=project,
        model=model,
        is_starred=is_starred,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Batch-load tags for all sessions to avoid N+1 queries
    tags_by_session = await _batch_load_tags(db, [s.id for s in items])

    list_items = []
    for s in items:
        item = SessionListItem.model_validate(s)
        item.tags = tags_by_session.get(s.id, [])
        list_items.append(item)

    return SessionListResponse(
        items=list_items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size < total),
    )


@router.get("/filters", response_model=FilterValues)
async def get_filters(
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> FilterValues:
    """Return distinct filter values for UI dropdowns."""
    fv = await sessions.get_session_filters(db, user.id)
    return FilterValues(
        sources=fv.sources,
        projects=fv.projects,
        models=fv.models,
    )


# ---------------------------------------------------------------------------
# Fixed-path routes — MUST be before /{session_id} to avoid capture
# ---------------------------------------------------------------------------


@router.get("/trash", response_model=SessionListResponse)
async def list_trashed_sessions(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SessionListResponse:
    """Return paginated list of soft-deleted sessions."""
    items, total = await sessions.list_trashed_sessions(
        db, user.id, page=page, page_size=page_size
    )
    return SessionListResponse(
        items=[_session_to_list_item(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size < total),
    )


@router.post("/batch", response_model=BatchResponse)
async def batch_operation(
    body: BatchRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BatchResponse:
    """Perform a batch operation on multiple sessions."""
    try:
        affected = await sessions.batch_operation(
            db, user.id, body.session_ids, body.action
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return BatchResponse(affected=affected)


# ---------------------------------------------------------------------------
# Parameterised routes — /{session_id}/...
# ---------------------------------------------------------------------------


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SessionDetail:
    """Return full session detail including assembled messages."""
    detail = await sessions.get_session_detail(db, user.id, session_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Build MessageDetail objects from AssembledMessage dataclasses
    message_details = [
        MessageDetail(
            id=m.id,
            role=m.role,
            ordinal=m.ordinal,
            tool_name=m.tool_name,
            tool_call_id=m.tool_call_id,
            tool_status=m.tool_status,
            input_tokens=m.input_tokens,
            output_tokens=m.output_tokens,
            started_at=m.started_at,
            ended_at=m.ended_at,
            content=m.content,
        )
        for m in detail.messages
    ]

    # Load actual tags for this session
    tag_stmt = (
        select(Tag.id, Tag.name, Tag.color)
        .join(SessionTag, SessionTag.tag_id == Tag.id)
        .where(SessionTag.session_id == session_id)
    )
    tag_result = await db.execute(tag_stmt)
    tags = [TagSummary(id=r.id, name=r.name, color=r.color) for r in tag_result.all()]

    s = detail.session
    return SessionDetail(
        id=s.id,
        session_key=s.session_key,
        source=s.source,
        started_at=s.started_at,
        last_message_at=s.last_message_at,
        duration_seconds=s.duration_seconds,
        total_messages=s.total_messages,
        user_messages=s.user_messages,
        assistant_messages=s.assistant_messages,
        total_input_tokens=s.total_input_tokens,
        total_output_tokens=s.total_output_tokens,
        project_name=s.project_name,
        model=s.model,
        title=s.title,
        is_starred=s.is_starred,
        created_at=s.created_at,
        summary=s.summary,
        content_key=s.content_key,
        content_size=s.content_size,
        raw_key=s.raw_key,
        raw_size=s.raw_size,
        content_hash=s.content_hash,
        raw_hash=s.raw_hash,
        parser_revision=s.parser_revision,
        schema_version=s.schema_version,
        ingested_at=s.ingested_at,
        messages=message_details,
        tags=tags,
    )


@router.get("/{session_id}/content")
async def get_session_content(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    """Download canonical session content from blob storage."""
    detail = await sessions.get_session_detail(db, user.id, session_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    content_key = detail.session.content_key
    if not content_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content available for this session",
        )

    storage = BlobStorageService(
        connection_string=settings.azure_storage_connection_string,
        container_name=settings.azure_storage_container_name,
    )

    try:
        compressed = await storage.download(content_key)
    except Exception as exc:
        logger.exception("Failed to download blob: %s", content_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve session content from storage",
        ) from exc

    # Canonical content is stored as gzip-compressed JSON
    try:
        raw = gzip.decompress(compressed)
        data = json.loads(raw)
    except Exception as exc:
        logger.exception("Failed to decompress/parse blob: %s", content_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse session content",
        ) from exc

    return JSONResponse(content=data)


# ---------------------------------------------------------------------------
# Star / Trash / Restore / Tags — /{session_id}/*
# ---------------------------------------------------------------------------


@router.patch("/{session_id}/star")
async def star_session(
    session_id: UUID,
    body: StarRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Toggle the star status of a session."""
    found = await sessions.star_session(db, user.id, session_id, body.is_starred)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"is_starred": body.is_starred}


@router.post("/{session_id}/trash", status_code=status.HTTP_204_NO_CONTENT)
async def trash_session(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Soft-delete a session."""
    found = await sessions.trash_session(db, user.id, session_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already trashed",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{session_id}/trash", status_code=status.HTTP_204_NO_CONTENT)
async def restore_session(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Restore a soft-deleted session."""
    found = await sessions.restore_session(db, user.id, session_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or not trashed",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{session_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def add_tag(
    session_id: UUID,
    tag_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Associate a tag with a session."""
    ok = await add_tag_to_session(db, user.id, session_id, tag_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{session_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_tag(
    session_id: UUID,
    tag_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Remove a tag from a session."""
    ok = await remove_tag_from_session(db, user.id, session_id, tag_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _batch_load_tags(
    db: AsyncSession,
    session_ids: list[UUID],
) -> dict[UUID, list[TagSummary]]:
    """Load tags for multiple sessions in a single query.

    Returns a dict mapping session_id → list[TagSummary].
    """
    if not session_ids:
        return {}
    tag_stmt = (
        select(SessionTag.session_id, Tag.id, Tag.name, Tag.color)
        .join(Tag, Tag.id == SessionTag.tag_id)
        .where(SessionTag.session_id.in_(session_ids))
    )
    tag_result = await db.execute(tag_stmt)
    tags_by_session: dict[UUID, list[TagSummary]] = {}
    for row in tag_result.all():
        tags_by_session.setdefault(row.session_id, []).append(
            TagSummary(id=row.id, name=row.name, color=row.color)
        )
    return tags_by_session


def _session_to_list_item(s: object) -> SessionListItem:
    """Convert a Session model instance to a SessionListItem schema."""
    return SessionListItem(
        id=s.id,  # type: ignore[attr-defined]
        session_key=s.session_key,  # type: ignore[attr-defined]
        source=s.source,  # type: ignore[attr-defined]
        started_at=s.started_at,  # type: ignore[attr-defined]
        last_message_at=s.last_message_at,  # type: ignore[attr-defined]
        duration_seconds=s.duration_seconds,  # type: ignore[attr-defined]
        total_messages=s.total_messages,  # type: ignore[attr-defined]
        user_messages=s.user_messages,  # type: ignore[attr-defined]
        assistant_messages=s.assistant_messages,  # type: ignore[attr-defined]
        total_input_tokens=s.total_input_tokens,  # type: ignore[attr-defined]
        total_output_tokens=s.total_output_tokens,  # type: ignore[attr-defined]
        project_name=s.project_name,  # type: ignore[attr-defined]
        model=s.model,  # type: ignore[attr-defined]
        title=s.title,  # type: ignore[attr-defined]
        is_starred=s.is_starred,  # type: ignore[attr-defined]
        created_at=s.created_at,  # type: ignore[attr-defined]
        tags=[],
    )
