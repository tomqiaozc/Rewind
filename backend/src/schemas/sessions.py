"""Pydantic response schemas for Phase 3 read APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── Helpers ──────────────────────────────────────────────────────────────────


class TagSummary(BaseModel):
    """Lightweight tag representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    color: str


class DayCount(BaseModel):
    """Single date + count pair for time-series charts."""

    date: str
    count: int


# ── Messages ─────────────────────────────────────────────────────────────────


class MessageDetail(BaseModel):
    """Message with content assembled from chunks."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    ordinal: int
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_status: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    content: str = ""


# ── Sessions ─────────────────────────────────────────────────────────────────


class SessionListItem(BaseModel):
    """Lightweight session schema for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_key: str
    source: str
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    project_name: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    is_starred: bool = False
    created_at: datetime
    tags: list[TagSummary] = []


class SessionListResponse(BaseModel):
    """Paginated session list."""

    items: list[SessionListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class SessionDetail(BaseModel):
    """Full session including messages."""

    model_config = ConfigDict(from_attributes=True)

    # Fields shared with SessionListItem
    id: UUID
    session_key: str
    source: str
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    project_name: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    is_starred: bool = False
    created_at: datetime
    tags: list[TagSummary] = []

    # Detail-only fields
    summary: Optional[str] = None
    content_key: Optional[str] = None
    content_size: Optional[int] = None
    raw_key: Optional[str] = None
    raw_size: Optional[int] = None
    content_hash: Optional[str] = None
    raw_hash: Optional[str] = None
    parser_revision: int
    schema_version: int
    ingested_at: Optional[datetime] = None
    messages: list[MessageDetail] = []


# ── Search ───────────────────────────────────────────────────────────────────


class SearchResult(BaseModel):
    """Single full-text search hit."""

    session_id: UUID
    session_title: Optional[str] = None
    source: str
    started_at: Optional[datetime] = None
    message_id: UUID
    ordinal: int
    snippet: str  # contains <mark> tags for highlighted terms
    role: str


class SearchResponse(BaseModel):
    """Paginated search results."""

    results: list[SearchResult]
    total: int
    query: str


# ── Dashboard / Filters ─────────────────────────────────────────────────────


class DashboardStats(BaseModel):
    """Aggregate statistics for the dashboard overview."""

    total_sessions: int
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    sessions_by_source: dict[str, int]
    sessions_by_day: list[DayCount]
    recent_sessions: list[SessionListItem]


class FilterValues(BaseModel):
    """Distinct filter values for UI dropdowns."""

    sources: list[str]
    projects: list[str]
    models: list[str]


# ── Star / Batch operations ─────────────────────────────────────────────────


class StarRequest(BaseModel):
    """Request body for toggling session star status."""

    is_starred: bool


class BatchRequest(BaseModel):
    """Request body for batch operations on sessions."""

    session_ids: list[str] = Field(..., min_length=1, max_length=500)
    action: str = Field(..., pattern=r"^(star|unstar|trash|restore)$")


class BatchResponse(BaseModel):
    """Response body for batch operations."""

    affected: int
