"""Session read API routes — list, detail, filters, and raw content."""
from __future__ import annotations

import gzip
import json
import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.auth.dependencies import get_current_user
from src.config import settings
from src.db.session import get_db
from src.schemas.sessions import (
    FilterValues,
    MessageDetail,
    SessionDetail,
    SessionListItem,
    SessionListResponse,
)
from src.services import sessions
from src.services.storage import BlobStorageService

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
    return SessionListResponse(
        items=[SessionListItem.model_validate(s) for s in items],
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
        tags=[],  # Tags are implemented in Phase 4
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
