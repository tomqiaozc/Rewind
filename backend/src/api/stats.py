"""Dashboard statistics API route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.schemas.sessions import DashboardStats, DayCount, SessionListItem
from src.services import stats

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = 90,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> DashboardStats:
    """Return aggregate dashboard statistics for the authenticated user."""
    data = await stats.get_dashboard_stats(db, user.id, days)
    return DashboardStats(
        total_sessions=data["total_sessions"],
        total_messages=data["total_messages"],
        total_input_tokens=data["total_input_tokens"],
        total_output_tokens=data["total_output_tokens"],
        sessions_by_source=data["sessions_by_source"],
        sessions_by_day=[
            DayCount(date=date, count=count) for date, count in data["sessions_by_day"]
        ],
        recent_sessions=[SessionListItem(**s) for s in data["recent_sessions"]],
    )
