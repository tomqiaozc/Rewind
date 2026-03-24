"""Project aggregation service.

Projects are virtual groupings — there is no projects table.  All data
is derived from the ``sessions`` table by grouping on ``project_name``.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, and_, cast, func, select

from src.models.session import Session

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def list_projects(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Return per-project aggregates for a user.

    Each dict contains: project_name, session_count, total_messages,
    total_input_tokens, total_output_tokens, total_duration_seconds,
    last_session_at, sources.
    """

    not_deleted = and_(
        Session.user_id == user_id,
        Session.deleted_at.is_(None),
        Session.project_name.isnot(None),
    )

    # ------------------------------------------------------------------
    # 1. Aggregate stats per project
    # ------------------------------------------------------------------
    agg_stmt = (
        select(
            Session.project_name,
            func.count(Session.id).label("session_count"),
            func.coalesce(func.sum(Session.total_messages), 0).label("total_messages"),
            func.coalesce(func.sum(Session.total_input_tokens), 0).label(
                "total_input_tokens"
            ),
            func.coalesce(func.sum(Session.total_output_tokens), 0).label(
                "total_output_tokens"
            ),
            func.coalesce(func.sum(Session.duration_seconds), 0).label(
                "total_duration_seconds"
            ),
            func.max(Session.started_at).label("last_session_at"),
        )
        .where(not_deleted)
        .group_by(Session.project_name)
        .order_by(func.count(Session.id).desc())
    )

    agg_rows = (await db.execute(agg_stmt)).all()

    # ------------------------------------------------------------------
    # 2. Distinct sources per project
    # ------------------------------------------------------------------
    sources_stmt = (
        select(
            Session.project_name,
            Session.source,
        )
        .where(not_deleted)
        .group_by(Session.project_name, Session.source)
    )

    sources_rows = (await db.execute(sources_stmt)).all()
    sources_map: dict[str, list[str]] = {}
    for row in sources_rows:
        sources_map.setdefault(row.project_name, []).append(row.source)

    # ------------------------------------------------------------------
    # 3. Assemble results
    # ------------------------------------------------------------------
    results: list[dict[str, Any]] = []
    for row in agg_rows:
        results.append(
            {
                "project_name": row.project_name,
                "session_count": row.session_count,
                "total_messages": row.total_messages,
                "total_input_tokens": row.total_input_tokens,
                "total_output_tokens": row.total_output_tokens,
                "total_duration_seconds": row.total_duration_seconds,
                "last_session_at": (
                    row.last_session_at.isoformat() if row.last_session_at else None
                ),
                "sources": sorted(sources_map.get(row.project_name, [])),
            }
        )

    return results


async def get_project_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Return daily session counts grouped by project for the last *days* days.

    NOTE: This uses ``cast(Session.started_at, Date)`` which requires
    PostgreSQL.  Tests should mock this function when running on SQLite.
    """

    cutoff = datetime.utcnow() - timedelta(days=days)

    not_deleted = and_(
        Session.user_id == user_id,
        Session.deleted_at.is_(None),
        Session.project_name.isnot(None),
        Session.started_at >= cutoff,
    )

    stmt = (
        select(
            cast(Session.started_at, Date).label("day"),
            Session.project_name,
            func.count(Session.id).label("cnt"),
        )
        .where(not_deleted)
        .group_by("day", Session.project_name)
        .order_by("day", Session.project_name)
    )

    rows = (await db.execute(stmt)).all()

    return [
        {
            "date": row.day.isoformat(),
            "project_name": row.project_name,
            "count": row.cnt,
        }
        for row in rows
    ]
