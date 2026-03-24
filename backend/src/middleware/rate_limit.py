"""Rate limiting middleware using slowapi."""
from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.api_rate_limit])


def setup_rate_limiting(app):  # type: ignore[no-untyped-def]
    """Register rate limiter with FastAPI app. Call from main.py."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
