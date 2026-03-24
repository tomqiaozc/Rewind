"""Pydantic schemas for projects API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    project_name: str
    session_count: int
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    total_duration_seconds: int
    last_session_at: Optional[str] = None
    sources: list[str] = []


class ProjectActivity(BaseModel):
    date: str
    project_name: str
    count: int
