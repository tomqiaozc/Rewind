"""SQLAlchemy models for sessions, messages, and message chunks."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    session_key: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)

    # Temporal
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Counts
    user_messages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    assistant_messages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_messages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Tokens
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total_cached_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    # Context
    project_ref: Mapped[Optional[str]] = mapped_column(Text)
    project_name: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Content references (Blob Storage keys)
    content_key: Mapped[Optional[str]] = mapped_column(Text)
    content_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    raw_key: Mapped[Optional[str]] = mapped_column(Text)
    raw_size: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Versioning (idempotent ingest)
    content_hash: Mapped[Optional[str]] = mapped_column(Text)
    raw_hash: Mapped[Optional[str]] = mapped_column(Text)
    parser_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # User organization
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (UniqueConstraint("user_id", "session_key"),)

    # Relationships
    messages: Mapped[List[Message]] = relationship(back_populates="session", cascade="all, delete")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    # Tool metadata
    tool_name: Mapped[Optional[str]] = mapped_column(Text)
    tool_call_id: Mapped[Optional[str]] = mapped_column(Text)
    tool_status: Mapped[Optional[str]] = mapped_column(Text)

    # Tokens
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("session_id", "ordinal"),)

    # Relationships
    session: Mapped[Session] = relationship(back_populates="messages")
    chunks: Mapped[List[MessageChunk]] = relationship(
        back_populates="message", cascade="all, delete"
    )


class MessageChunk(Base):
    __tablename__ = "message_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_context: Mapped[Optional[str]] = mapped_column(Text)

    # FTS: tsvector column — GENERATED ALWAYS AS is handled in the migration,
    # not in the model. Mark as Computed so SQLAlchemy excludes it from INSERT/UPDATE.
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), nullable=True
    )

    __table_args__ = (UniqueConstraint("message_id", "chunk_index"),)

    # Relationships
    message: Mapped[Message] = relationship(back_populates="chunks")
