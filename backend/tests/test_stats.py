"""Tests for the stats API route (Phase 3a dashboard statistics).

NOTE: The stats service uses ``cast(Session.started_at, Date)`` which is a
PostgreSQL-specific operation.  SQLite does not support the ``Date`` type
cast the same way, so we test the service function with a mock and the API
route separately.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.stats import router as stats_router
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import Base, User
from src.models.session import Session

# ---------------------------------------------------------------------------
# BFF proxy auth header — matches config default
# ---------------------------------------------------------------------------
BFF_SECRET = "dev-backend-secret-change-in-production"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine():
    """Create a SQLite async engine and provision all tables."""
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)

    from sqlalchemy.dialects.postgresql import TSVECTOR
    from sqlalchemy.ext.compiler import compiles

    @compiles(TSVECTOR, "sqlite")
    def _compile_tsvector(element, compiler, **kw):  # noqa: ANN001,ANN202
        return "TEXT"

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001,ANN202
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def db_session(engine):
    """Yield an async session bound to the in-memory SQLite engine."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture()
async def user(db_session: AsyncSession) -> User:
    """Insert and return a test user."""
    u = User(id=uuid.uuid4(), email="stats-test@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture()
async def sample_sessions(db_session: AsyncSession, user: User):
    """Create a few sessions for stats testing."""
    now = datetime.now(timezone.utc)
    sessions = []
    for i in range(3):
        s = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            session_key=f"stats-session-{i}",
            source="claude" if i < 2 else "opencode",
            started_at=now - timedelta(days=i),
            last_message_at=now - timedelta(days=i),
            snapshot_at=now,
            total_messages=10 * (i + 1),
            user_messages=5 * (i + 1),
            assistant_messages=5 * (i + 1),
            total_input_tokens=100 * (i + 1),
            total_output_tokens=200 * (i + 1),
            total_cached_tokens=0,
            parser_revision=1,
            schema_version=1,
            content_hash=f"stats-hash-{i}",
            raw_hash=f"stats-raw-{i}",
        )
        db_session.add(s)
        sessions.append(s)
    await db_session.commit()
    return sessions


def _build_test_app():
    """Create a minimal FastAPI app with the stats router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(stats_router)
    return test_app


# ---------------------------------------------------------------------------
# API route tests — using mocked service to avoid SQLite/Date cast issues
# ---------------------------------------------------------------------------


class TestStatsApiRoute:
    """Tests for GET /api/stats using a mocked service layer."""

    async def test_api_stats(self, user: User, engine) -> None:
        """GET /api/stats returns proper structure with mocked service data."""
        app = _build_test_app()

        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async def _override_db():  # noqa: ANN202
            async with session_factory() as session:
                yield session

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user

        mock_stats_data: dict[str, Any] = {
            "total_sessions": 3,
            "total_messages": 60,
            "total_input_tokens": 600,
            "total_output_tokens": 1200,
            "sessions_by_source": {"claude": 2, "opencode": 1},
            "sessions_by_day": [
                ("2025-01-01", 1),
                ("2025-01-02", 2),
            ],
            "recent_sessions": [
                {
                    "id": str(uuid.uuid4()),
                    "session_key": "s1",
                    "source": "claude",
                    "started_at": "2025-01-02T12:00:00",
                    "last_message_at": "2025-01-02T13:00:00",
                    "duration_seconds": 3600,
                    "total_messages": 20,
                    "user_messages": 10,
                    "assistant_messages": 10,
                    "total_input_tokens": 200,
                    "total_output_tokens": 400,
                    "project_name": "my-project",
                    "model": "claude-3.5-sonnet",
                    "title": "Test Session",
                    "is_starred": False,
                    "created_at": "2025-01-02T12:00:00",
                },
            ],
        }

        with patch(
            "src.api.stats.stats.get_dashboard_stats",
            new_callable=AsyncMock,
            return_value=mock_stats_data,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.get("/api/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 3
        assert data["total_messages"] == 60
        assert data["total_input_tokens"] == 600
        assert data["total_output_tokens"] == 1200
        assert data["sessions_by_source"] == {"claude": 2, "opencode": 1}
        assert len(data["sessions_by_day"]) == 2
        assert data["sessions_by_day"][0]["date"] == "2025-01-01"
        assert data["sessions_by_day"][0]["count"] == 1
        assert len(data["recent_sessions"]) == 1
        assert data["recent_sessions"][0]["source"] == "claude"
        app.dependency_overrides.clear()

    async def test_api_stats_unauthorized(self) -> None:
        """Requests without auth headers should be rejected with 401."""
        from unittest.mock import MagicMock

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(stats_router)

        async def _mock_db():  # noqa: ANN202
            mock = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock.execute.return_value = result_mock
            yield mock

        app.dependency_overrides[get_db] = _mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/stats")
        assert resp.status_code == 401
        app.dependency_overrides.clear()


class TestStatsApiWithRealDb:
    """Test stats endpoint with real SQLite DB — exercises the service function.

    The ``cast(Session.started_at, Date)`` in ``get_dashboard_stats`` does not
    work on SQLite, so this test is expected to exercise only the parts of the
    service that don't use Date casting.  We mark it ``xfail`` if SQLite raises
    an operational error due to the Date cast.
    """

    @pytest.mark.xfail(
        reason="SQLite does not support cast(..., Date)",
        strict=False,
    )
    async def test_api_stats_with_real_db(
        self, user: User, engine, sample_sessions
    ) -> None:
        """If SQLite happens to support the query, verify the response shape."""
        app = _build_test_app()

        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async def _override_db():  # noqa: ANN202
            async with session_factory() as session:
                yield session

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/stats")

        # If we get here, the query worked on SQLite
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "total_messages" in data
        assert "sessions_by_source" in data
        assert "sessions_by_day" in data
        assert "recent_sessions" in data
        app.dependency_overrides.clear()
