"""Pydantic request/response schemas for the ingest API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.core.constants import MAX_BATCH_SIZE


class SessionSnapshot(BaseModel):
    """A single session snapshot from CLI."""

    session_key: str
    source: str  # claude, opencode, gemini, codex, copilot
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    snapshot_at: datetime
    user_messages: int = 0
    assistant_messages: int = 0
    total_messages: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    project_ref: Optional[str] = None
    project_name: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    content_hash: Optional[str] = None
    raw_hash: Optional[str] = None
    parser_revision: int
    schema_version: int
    messages: list[Any] = Field(default_factory=list)


class BatchIngestRequest(BaseModel):
    """Batch metadata upsert request."""

    sessions: list[SessionSnapshot] = Field(max_length=MAX_BATCH_SIZE)


class BatchIngestResponse(BaseModel):
    """Batch metadata upsert response."""

    ingested: int  # number of sessions actually inserted/updated
    skipped: int  # unchanged sessions (same hashes + versions)


class PresignRequest(BaseModel):
    """Request a pre-signed SAS URL for direct raw upload."""

    session_key: str
    raw_hash: str


class PresignResponse(BaseModel):
    """Pre-signed SAS URL for direct raw upload."""

    upload_url: str
    blob_key: str


class RawConfirmRequest(BaseModel):
    """Confirm raw upload after direct upload to blob storage."""

    raw_hash: str
    raw_size: int
