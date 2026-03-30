"""SQLAlchemy models for Rewind."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email_verified: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    image: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    accounts: Mapped[List[Account]] = relationship(back_populates="user", cascade="all, delete")
    api_keys: Mapped[List[ApiKey]] = relationship(back_populates="user", cascade="all, delete")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    token_type: Mapped[Optional[str]] = mapped_column(String(50))
    scope: Mapped[Optional[str]] = mapped_column(Text)
    id_token: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("provider", "provider_account_id"),)

    # Relationships
    user: Mapped[User] = relationship(back_populates="accounts")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    key_prefix: Mapped[Optional[str]] = mapped_column(String(8))
    device_name: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped[User] = relationship(back_populates="api_keys")
