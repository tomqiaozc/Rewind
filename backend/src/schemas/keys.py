"""Pydantic schemas for API key management."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApiKeyResponse(BaseModel):
    """Schema for API key list responses (no secret)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    device_name: Optional[str] = None
    key_prefix: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None
