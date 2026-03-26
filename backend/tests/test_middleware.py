"""Tests for security middleware."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request  # noqa: TCH002

from src.middleware.rate_limit import limiter, setup_rate_limiting
from src.middleware.request_logging import RequestLoggingMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware

# ── Rate Limiting Tests ──


def test_rate_limiter_exists():
    assert limiter is not None
    assert isinstance(limiter, Limiter)


def test_setup_rate_limiting_registers_on_app():
    app = FastAPI()
    setup_rate_limiting(app)
    assert hasattr(app.state, "limiter")


def test_rate_limit_returns_429():
    """Test that exceeding rate limit returns 429."""
    test_limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"])
    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/test")
    @test_limiter.limit("2/minute")
    async def test_endpoint(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/test").status_code == 200
    assert client.get("/test").status_code == 200
    assert client.get("/test").status_code == 429


# ── Security Headers Tests ──


def test_security_headers_present():
    """Test that security headers are added to responses."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_hsts_not_set_without_trusted_host():
    """Test that HSTS is not set when trusted_host is empty."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert "Strict-Transport-Security" not in response.headers


# ── Request Logging Tests ──


def test_request_id_header():
    """Test that X-Request-ID header is added."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 8


def test_request_logging_logs_request(caplog):
    """Test that requests are logged."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="rewind.access"):
        client.get("/test")

    assert any("GET /test 200" in record.message for record in caplog.records)
