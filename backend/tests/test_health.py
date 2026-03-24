"""Tests for health check endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.main import app


async def _mock_db_session():
    """Yield a mock async session that responds to execute."""
    mock = AsyncMock(spec=AsyncSession)
    mock.execute = AsyncMock(return_value=None)
    yield mock


@pytest.fixture()
def _override_db():
    app.dependency_overrides[get_db] = _mock_db_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.usefixtures("_override_db")
async def test_health_check() -> None:
    """Health check should return 200 with status ok and db info."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.usefixtures("_override_db")
async def test_health_check_db_error() -> None:
    """Health check should return degraded when DB is down."""

    async def _failing_db():
        mock = AsyncMock(spec=AsyncSession)
        mock.execute = AsyncMock(side_effect=Exception("connection refused"))
        yield mock

    app.dependency_overrides[get_db] = _failing_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "error"
