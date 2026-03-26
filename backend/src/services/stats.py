"""Dashboard aggregate statistics service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, and_, cast, desc, func, select

from src.models.session import Session

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def get_dashboard_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 90,
) -> dict[str, Any]:
    """Return dashboard overview statistics for a user.

    Parameters
    ----------
    db:
        Async SQLAlchemy session.
    user_id:
        The user whose stats to retrieve.
    days:
        Number of days to include in the sessions-by-day breakdown
        (default 90).

    Returns
    -------
    dict with keys:
        total_sessions, total_messages, total_input_tokens,
        total_output_tokens, sessions_by_source, sessions_by_day,
        recent_sessions.
    """

    not_deleted = and_(
        Session.user_id == user_id,
        Session.deleted_at.is_(None),
    )

    # ------------------------------------------------------------------
    # 1. Scalar aggregates (single query)
    # ------------------------------------------------------------------
    agg_stmt = select(
        func.count(Session.id).label("total_sessions"),
        func.coalesce(func.sum(Session.total_messages), 0).label("total_messages"),
        func.coalesce(func.sum(Session.total_input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(Session.total_output_tokens), 0).label("total_output_tokens"),
    ).where(not_deleted)

    agg_row = (await db.execute(agg_stmt)).one()

    # ------------------------------------------------------------------
    # 2. Sessions grouped by source
    # ------------------------------------------------------------------
    by_source_stmt = (
        select(
            Session.source,
            func.count(Session.id).label("cnt"),
        )
        .where(not_deleted)
        .group_by(Session.source)
    )

    by_source_rows = (await db.execute(by_source_stmt)).all()
    sessions_by_source: dict[str, int] = {row.source: row.cnt for row in by_source_rows}

    # ------------------------------------------------------------------
    # 3. Sessions grouped by day (last N days)
    # ------------------------------------------------------------------
    cutoff = datetime.utcnow() - timedelta(days=days)

    by_day_stmt = (
        select(
            cast(Session.started_at, Date).label("day"),
            func.count(Session.id).label("cnt"),
        )
        .where(
            and_(
                not_deleted,
                Session.started_at >= cutoff,
            )
        )
        .group_by("day")
        .order_by("day")
    )

    by_day_rows = (await db.execute(by_day_stmt)).all()
    sessions_by_day: list[tuple[str, int]] = [(row.day.isoformat(), row.cnt) for row in by_day_rows]

    # ------------------------------------------------------------------
    # 4. Recent sessions (last 10)
    # ------------------------------------------------------------------
    recent_stmt = (
        select(
            Session.id,
            Session.session_key,
            Session.source,
            Session.started_at,
            Session.last_message_at,
            Session.duration_seconds,
            Session.total_messages,
            Session.user_messages,
            Session.assistant_messages,
            Session.total_input_tokens,
            Session.total_output_tokens,
            Session.project_name,
            Session.model,
            Session.title,
            Session.is_starred,
            Session.created_at,
        )
        .where(not_deleted)
        .order_by(desc(Session.last_message_at))
        .limit(10)
    )

    recent_rows = (await db.execute(recent_stmt)).all()
    recent_sessions: list[dict[str, Any]] = [
        {
            "id": str(row.id),
            "session_key": row.session_key,
            "source": row.source,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "last_message_at": (row.last_message_at.isoformat() if row.last_message_at else None),
            "duration_seconds": row.duration_seconds,
            "total_messages": row.total_messages,
            "user_messages": row.user_messages,
            "assistant_messages": row.assistant_messages,
            "total_input_tokens": row.total_input_tokens,
            "total_output_tokens": row.total_output_tokens,
            "project_name": row.project_name,
            "model": row.model,
            "title": row.title,
            "is_starred": row.is_starred,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in recent_rows
    ]

    # ------------------------------------------------------------------
    # Assemble result
    # ------------------------------------------------------------------
    return {
        "total_sessions": agg_row.total_sessions,
        "total_messages": agg_row.total_messages,
        "total_input_tokens": agg_row.total_input_tokens,
        "total_output_tokens": agg_row.total_output_tokens,
        "sessions_by_source": sessions_by_source,
        "sessions_by_day": sessions_by_day,
        "recent_sessions": recent_sessions,
    }
