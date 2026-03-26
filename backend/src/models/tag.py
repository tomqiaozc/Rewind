"""SQLAlchemy models for tags and session-tag associations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.base import User
    from src.models.session import Session


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False, default="#6b7280")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", lazy="selectin")
    sessions: Mapped[List[SessionTag]] = relationship(
        "SessionTag", back_populates="tag", cascade="all, delete-orphan"
    )


class SessionTag(Base):
    __tablename__ = "session_tags"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    # Relationships
    tag: Mapped[Tag] = relationship("Tag", back_populates="sessions", lazy="selectin")
    session: Mapped[Session] = relationship("Session", lazy="selectin")
