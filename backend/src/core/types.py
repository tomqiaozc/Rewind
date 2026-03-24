from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal["claude", "opencode", "gemini", "codex", "copilot"]
MessageRole = Literal["user", "assistant", "system", "tool"]


class CanonicalMessage(BaseModel):
    """Represents a single message within a coding session."""

    role: MessageRole
    ordinal: int = Field(ge=0)
    content: str

    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_status: Optional[str] = None

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class CanonicalSession(BaseModel):
    """Represents a parsed session snapshot — the canonical data model."""

    session_key: str
    source: SourceType
    started_at: datetime
    last_message_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    snapshot_at: datetime

    user_messages: int
    assistant_messages: int
    total_messages: int

    total_input_tokens: Optional[int] = None
    total_output_tokens: Optional[int] = None
    total_cached_tokens: Optional[int] = None

    project_ref: Optional[str] = None
    project_name: Optional[str] = None
    model: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None

    content_hash: str
    raw_hash: str
    parser_revision: int
    schema_version: int

    messages: list[CanonicalMessage]


class RawSessionArchive(BaseModel):
    """Raw session data before parsing, stored for reprocessing."""

    session_key: str
    source: SourceType
    raw_data: Any
    snapshot_at: datetime
