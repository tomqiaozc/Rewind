"""Session query service — listing, detail, and filter retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import and_, asc, desc, func, select

from src.models.session import Message, MessageChunk, Session

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AssembledMessage:
    """A message with its content assembled from chunks."""

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    ordinal: int
    content: str
    tool_name: str | None
    tool_call_id: str | None
    tool_status: str | None
    input_tokens: int
    output_tokens: int
    started_at: object | None  # datetime, kept generic for forward compat
    ended_at: object | None


@dataclass
class SessionDetail:
    """A session with all its assembled messages."""

    session: Session
    messages: list[AssembledMessage]


@dataclass
class FilterValues:
    """Distinct values available for filter dropdowns."""

    sources: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Sort helpers
# ---------------------------------------------------------------------------

_SORT_COLUMNS = {
    "last_message_at": Session.last_message_at,
    "started_at": Session.started_at,
    "created_at": Session.created_at,
    "total_messages": Session.total_messages,
    "total_input_tokens": Session.total_input_tokens,
    "total_output_tokens": Session.total_output_tokens,
    "duration_seconds": Session.duration_seconds,
}


# ---------------------------------------------------------------------------
# 1. list_sessions
# ---------------------------------------------------------------------------


async def list_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    source: str | None = None,
    project: str | None = None,
    model: str | None = None,
    is_starred: bool | None = None,
    sort_by: str = "last_message_at",
    sort_order: str = "desc",
    include_deleted: bool = False,
) -> tuple[list[Session], int]:
    """Return a paginated list of sessions for *user_id*.

    Returns ``(items, total_count)`` where *items* is at most *page_size*
    rows and *total_count* is the unfiltered (but ownership + soft-delete
    scoped) count that the client can use for pagination controls.
    """

    # -- base conditions ---------------------------------------------------
    conditions = [Session.user_id == user_id]

    if not include_deleted:
        conditions.append(Session.deleted_at.is_(None))

    # -- optional filters --------------------------------------------------
    if source is not None:
        conditions.append(Session.source == source)
    if project is not None:
        conditions.append(Session.project_name == project)
    if model is not None:
        conditions.append(Session.model == model)
    if is_starred is not None:
        conditions.append(Session.is_starred == is_starred)

    where_clause = and_(*conditions)

    # -- total count -------------------------------------------------------
    count_stmt = select(func.count()).select_from(Session).where(where_clause)
    total_count: int = (await db.execute(count_stmt)).scalar_one()

    # -- ordered page ------------------------------------------------------
    sort_col = _SORT_COLUMNS.get(sort_by, Session.last_message_at)
    order_fn = desc if sort_order == "desc" else asc

    items_stmt = (
        select(Session)
        .where(where_clause)
        .order_by(order_fn(sort_col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(items_stmt)
    items: list[Session] = list(result.scalars().all())

    return items, total_count


# ---------------------------------------------------------------------------
# 2. get_session_detail
# ---------------------------------------------------------------------------


async def get_session_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SessionDetail | None:
    """Load a single session with all messages and their assembled content.

    Returns ``None`` when the session does not exist or does not belong to
    *user_id*.
    """

    # -- fetch session -----------------------------------------------------
    session_stmt = select(Session).where(
        and_(Session.id == session_id, Session.user_id == user_id)
    )
    session: Session | None = (await db.execute(session_stmt)).scalar_one_or_none()

    if session is None:
        return None

    # -- fetch messages with chunks in one query ---------------------------
    msg_stmt = (
        select(Message, MessageChunk)
        .outerjoin(MessageChunk, MessageChunk.message_id == Message.id)
        .where(Message.session_id == session_id)
        .order_by(Message.ordinal, MessageChunk.chunk_index)
    )

    rows = (await db.execute(msg_stmt)).all()

    # -- assemble messages from chunks -------------------------------------
    messages_map: dict[uuid.UUID, dict] = {}
    message_order: list[uuid.UUID] = []

    for msg, chunk in rows:
        if msg.id not in messages_map:
            messages_map[msg.id] = {
                "msg": msg,
                "chunks": [],
            }
            message_order.append(msg.id)
        if chunk is not None:
            messages_map[msg.id]["chunks"].append(chunk)

    assembled: list[AssembledMessage] = []
    for msg_id in message_order:
        entry = messages_map[msg_id]
        msg = entry["msg"]
        # Sort chunks by index to be safe (query already orders, but dict
        # grouping could theoretically reorder within the same ordinal).
        sorted_chunks: list[MessageChunk] = sorted(
            entry["chunks"], key=lambda c: c.chunk_index
        )
        content = "".join(c.content for c in sorted_chunks)

        assembled.append(
            AssembledMessage(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                ordinal=msg.ordinal,
                content=content,
                tool_name=msg.tool_name,
                tool_call_id=msg.tool_call_id,
                tool_status=msg.tool_status,
                input_tokens=msg.input_tokens,
                output_tokens=msg.output_tokens,
                started_at=msg.started_at,
                ended_at=msg.ended_at,
            )
        )

    return SessionDetail(session=session, messages=assembled)


# ---------------------------------------------------------------------------
# 3. get_session_filters
# ---------------------------------------------------------------------------


async def get_session_filters(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> FilterValues:
    """Return the distinct filter values available for the user's sessions.

    Only considers non-deleted sessions so that archived sessions don't
    pollute the dropdown choices.
    """

    base_where = and_(Session.user_id == user_id, Session.deleted_at.is_(None))

    sources_stmt = (
        select(Session.source)
        .where(base_where)
        .distinct()
        .order_by(Session.source)
    )
    projects_stmt = (
        select(Session.project_name)
        .where(and_(base_where, Session.project_name.isnot(None)))
        .distinct()
        .order_by(Session.project_name)
    )
    models_stmt = (
        select(Session.model)
        .where(and_(base_where, Session.model.isnot(None)))
        .distinct()
        .order_by(Session.model)
    )

    sources_result = await db.execute(sources_stmt)
    projects_result = await db.execute(projects_stmt)
    models_result = await db.execute(models_stmt)

    return FilterValues(
        sources=[row[0] for row in sources_result.all()],
        projects=[row[0] for row in projects_result.all()],
        models=[row[0] for row in models_result.all()],
    )
