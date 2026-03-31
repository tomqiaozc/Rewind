"""Full-text search service with XSS-safe snippet extraction.

Supports two search paths:

* **FTS** — PostgreSQL ``tsvector``/``tsquery`` for Latin-script text.
* **CJK** — ``ILIKE`` backed by a ``pg_trgm`` GIN index for Chinese,
  Japanese, and Korean text where whitespace-based tokenisation fails.

The path is chosen automatically based on the characters in the query.
Mixed queries (e.g. ``"fix 用户认证"``) combine both paths with AND.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, literal, select

from src.core.cjk import extract_cjk_and_latin
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


def highlight_substring(content: str, query: str, context_chars: int = 80) -> str:
    """Generate an HTML snippet for a substring match (used for CJK queries).

    Finds the first case-insensitive occurrence of *query* in *content*,
    extracts surrounding context, HTML-escapes everything, then wraps the
    match in ``<mark>`` tags.  Follows the same XSS-safe contract as
    :func:`sanitize_snippet`.
    """
    lower_content = content.lower()
    lower_query = query.lower()
    pos = lower_content.find(lower_query)
    if pos == -1:
        # Fallback: return the start of the content, escaped.
        return html.escape(content[: context_chars * 2], quote=True)

    start = max(0, pos - context_chars)
    end = min(len(content), pos + len(query) + context_chars)

    before = content[start:pos]
    match = content[pos : pos + len(query)]
    after = content[pos + len(query) : end]

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""

    return (
        html.escape(prefix + before, quote=True)
        + "<mark>"
        + html.escape(match, quote=True)
        + "</mark>"
        + html.escape(after + suffix, quote=True)
    )


def _escape_like(value: str) -> str:
    """Escape LIKE-pattern metacharacters in user input."""
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


async def search_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    source_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Search message chunks via PostgreSQL full-text search / trigram.

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

    cjk_part, latin_part = extract_cjk_and_latin(query)
    use_cjk = bool(cjk_part)
    use_fts = bool(latin_part)

    # If nothing useful was extracted, fall back to the raw query via FTS.
    if not use_cjk and not use_fts:
        use_fts = True
        latin_part = query

    # -- base filter conditions ------------------------------------------------
    filters: list[Any] = [
        Session.user_id == user_id,
        Session.deleted_at.is_(None),
    ]
    if source_filter is not None:
        filters.append(Session.source == source_filter)

    # -- CJK path: ILIKE with pg_trgm index -----------------------------------
    if use_cjk:
        safe_cjk = _escape_like(cjk_part)
        filters.append(MessageChunk.content.ilike(f"%{safe_cjk}%"))

    # -- FTS path: tsvector/tsquery --------------------------------------------
    tsquery = None
    if use_fts:
        tsquery = func.plainto_tsquery("simple", latin_part)
        filters.append(MessageChunk.search_vector.op("@@")(tsquery))

    # -- SELECT columns --------------------------------------------------------
    select_cols = [
        Session.id.label("session_id"),
        Session.title.label("session_title"),
        Session.source,
        Session.started_at,
        Message.id.label("message_id"),
        Message.ordinal,
        Message.role,
        MessageChunk.content,
    ]

    if tsquery is not None:
        headline = func.ts_headline(
            "simple",
            MessageChunk.content,
            tsquery,
            "StartSel=\\x01, StopSel=\\x02, MaxWords=40, MinWords=20",
        ).label("headline")
        rank = func.ts_rank(MessageChunk.search_vector, tsquery).label("rank")
        select_cols.extend([headline, rank])
    else:
        select_cols.extend([
            literal(None).label("headline"),
            literal(0).label("rank"),
        ])

    # -- main query ------------------------------------------------------------
    stmt = (
        select(*select_cols)
        .join(Message, Message.id == MessageChunk.message_id)
        .join(Session, Session.id == MessageChunk.session_id)
        .where(and_(*filters))
        .limit(limit)
        .offset(offset)
    )

    if use_fts:
        stmt = stmt.order_by(select_cols[-1].desc())  # rank DESC
    else:
        stmt = stmt.order_by(Session.started_at.desc().nulls_last())

    result = await db.execute(stmt)
    rows = result.all()

    results: list[dict[str, Any]] = []
    for row in rows:
        if row.headline is not None:
            snippet = sanitize_snippet(row.headline)
        else:
            snippet = highlight_substring(row.content, cjk_part)
        results.append({
            "session_id": row.session_id,
            "session_title": row.session_title,
            "source": row.source,
            "started_at": row.started_at,
            "message_id": row.message_id,
            "ordinal": row.ordinal,
            "snippet": snippet,
            "role": row.role,
        })

    # -- total count -----------------------------------------------------------
    count_stmt = (
        select(func.count())
        .select_from(MessageChunk)
        .join(Message, Message.id == MessageChunk.message_id)
        .join(Session, Session.id == MessageChunk.session_id)
        .where(and_(*filters))
    )

    total_count = (await db.execute(count_stmt)).scalar_one()

    return results, total_count
