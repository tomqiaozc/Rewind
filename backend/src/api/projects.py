"""Projects API routes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.schemas.projects import ProjectActivity, ProjectSummary
from src.services import projects as projects_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[ProjectSummary]:
    """Return project summaries for the authenticated user."""
    items = await projects_service.list_projects(db, user.id)
    return [ProjectSummary(**item) for item in items]


@router.get("/activity", response_model=list[ProjectActivity])
async def get_project_activity(
    days: int = 30,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[ProjectActivity]:
    """Return daily session counts by project for the authenticated user."""
    items = await projects_service.get_project_activity(db, user.id, days)
    return [ProjectActivity(**item) for item in items]
