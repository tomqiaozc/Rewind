"""Full-text search service with XSS-safe snippet extraction."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, select

from src.models.session import Message, MessageChunk, Session

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

# Control-character delimiters for ts_headline.  These are replaced with
# <mark>/<\/mark> *after* HTML-escaping so that user-controlled text can
# never inject markup.
SNIPPET_OPEN = "\x01"
SNIPPET_CLOSE = "\x02"


def sanitize_snippet(raw: str) -> str:
    """HTML-escape a ts_headline snippet, then swap control-char delimiters
    for ``<mark>`` tags.

    The two-step approach guarantees that any ``<`` or ``>`` inside the
    original content is escaped *before* we introduce our own safe HTML,
    preventing XSS via crafted session content.
    """
    escaped = html.escape(raw, quote=True)
    return escaped.replace(SNIPPET_OPEN, "<mark>").replace(SNIPPET_CLOSE, "</mark>")


async def search_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    source_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Search message chunks via PostgreSQL full-text search.

    Returns ``(results, total_count)`` where each result dict contains:

    * ``session_id``
    * ``session_title``
    * ``source``
    * ``started_at``
    * ``message_id``
    * ``ordinal``
    * ``snippet``  — sanitized HTML snippet
    * ``role``
    """

    tsquery = func.plainto_tsquery("simple", query)

    # -- shared filter conditions -------------------------------------------
    filters = [
        MessageChunk.search_vector.op("@@")(tsquery),
        Session.user_id == user_id,
        Session.deleted_at.is_(None),
    ]
    if source_filter is not None:
        filters.append(Session.source == source_filter)

    # -- headline expression ------------------------------------------------
    headline = func.ts_headline(
        "simple",
        MessageChunk.content,
        tsquery,
        "StartSel=\\x01, StopSel=\\x02, MaxWords=40, MinWords=20",
    ).label("snippet")

    rank = func.ts_rank(MessageChunk.search_vector, tsquery).label("rank")

    # -- main query ---------------------------------------------------------
    stmt = (
        select(
            Session.id.label("session_id"),
            Session.title.label("session_title"),
            Session.source,
            Session.started_at,
            Message.id.label("message_id"),
            Message.ordinal,
            Message.role,
            headline,
            rank,
        )
        .join(Message, Message.id == MessageChunk.message_id)
        .join(Session, Session.id == MessageChunk.session_id)
        .where(and_(*filters))
        .order_by(rank.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    rows = result.all()

    results: list[dict[str, Any]] = [
        {
            "session_id": row.session_id,
            "session_title": row.session_title,
            "source": row.source,
            "started_at": row.started_at,
            "message_id": row.message_id,
            "ordinal": row.ordinal,
            "snippet": sanitize_snippet(row.snippet),
            "role": row.role,
        }
        for row in rows
    ]

    # -- total count --------------------------------------------------------
    count_stmt = (
        select(func.count())
        .select_from(MessageChunk)
        .join(Message, Message.id == MessageChunk.message_id)
        .join(Session, Session.id == MessageChunk.session_id)
        .where(and_(*filters))
    )

    total_count = (await db.execute(count_stmt)).scalar_one()

    return results, total_count
