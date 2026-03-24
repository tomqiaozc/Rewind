"""Pydantic schemas for tag CRUD operations."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """Schema for creating a new tag."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6b7280", pattern=r"^#[0-9a-fA-F]{6}$")


class TagUpdate(BaseModel):
    """Schema for updating an existing tag."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class TagResponse(BaseModel):
    """Schema for tag responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: str
    created_at: Optional[str] = None
    session_count: int = 0
