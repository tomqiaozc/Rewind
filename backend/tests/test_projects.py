"""Tests for the projects service and API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.projects import router as projects_router
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import Base, User
from src.models.session import Session
from src.services.projects import list_projects

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
async def session_factory(engine):
    """Return a session factory bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture()
async def db_session(session_factory):
    """Yield an async session bound to the in-memory SQLite engine."""
    async with session_factory() as session:
        yield session


@pytest.fixture()
async def user(db_session: AsyncSession) -> User:
    """Insert and return a test user."""
    u = User(id=uuid.uuid4(), email="projects-test@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


def _make_session(
    user_id: uuid.UUID,
    idx: int,
    *,
    project_name: str | None = None,
    source: str = "claude",
    total_messages: int = 10,
    total_input_tokens: int = 100,
    total_output_tokens: int = 200,
    duration_seconds: int | None = 60,
    deleted_at: datetime | None = None,
) -> Session:
    """Helper to build a Session instance for testing."""
    now = datetime.now(timezone.utc)
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        session_key=f"proj-session-{idx}",
        source=source,
        started_at=now,
        last_message_at=now,
        snapshot_at=now,
        total_messages=total_messages,
        user_messages=total_messages // 2,
        assistant_messages=total_messages // 2,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_cached_tokens=0,
        duration_seconds=duration_seconds,
        parser_revision=1,
        schema_version=1,
        content_hash=f"proj-hash-{idx}",
        raw_hash=f"proj-raw-{idx}",
        project_name=project_name,
        deleted_at=deleted_at,
    )


def _build_test_app():
    """Create a minimal FastAPI app with the projects router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(projects_router)
    return test_app


@pytest.fixture()
async def client(session_factory, user: User):
    """Yield an httpx AsyncClient wired to the test app with SQLite DB."""
    app = _build_test_app()

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
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestListProjects:
    """Tests for the list_projects service function."""

    async def test_list_projects(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Seed 3 sessions across 2 projects, verify aggregates."""
        # Project A: 2 sessions
        db_session.add(
            _make_session(
                user.id, 0, project_name="alpha",
                total_messages=10, total_input_tokens=100,
                total_output_tokens=200, duration_seconds=60,
            )
        )
        db_session.add(
            _make_session(
                user.id, 1, project_name="alpha",
                total_messages=20, total_input_tokens=300,
                total_output_tokens=400, duration_seconds=120,
            )
        )
        # Project B: 1 session
        db_session.add(
            _make_session(
                user.id, 2, project_name="beta",
                total_messages=5, total_input_tokens=50,
                total_output_tokens=75, duration_seconds=30,
            )
        )
        await db_session.commit()

        results = await list_projects(db_session, user.id)
        assert len(results) == 2

        # Ordered by session_count DESC, so alpha first
        alpha = results[0]
        assert alpha["project_name"] == "alpha"
        assert alpha["session_count"] == 2
        assert alpha["total_messages"] == 30
        assert alpha["total_input_tokens"] == 400
        assert alpha["total_output_tokens"] == 600
        assert alpha["total_duration_seconds"] == 180
        assert alpha["last_session_at"] is not None

        beta = results[1]
        assert beta["project_name"] == "beta"
        assert beta["session_count"] == 1
        assert beta["total_messages"] == 5

    async def test_list_projects_excludes_deleted(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Trashed session's project should not be counted."""
        now = datetime.now(timezone.utc)
        db_session.add(
            _make_session(user.id, 10, project_name="alive")
        )
        db_session.add(
            _make_session(
                user.id, 11, project_name="dead", deleted_at=now,
            )
        )
        await db_session.commit()

        results = await list_projects(db_session, user.id)
        names = [r["project_name"] for r in results]
        assert "alive" in names
        assert "dead" not in names

    async def test_list_projects_excludes_null_project(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Sessions with project_name=None should not appear."""
        db_session.add(_make_session(user.id, 20, project_name=None))
        db_session.add(_make_session(user.id, 21, project_name="visible"))
        await db_session.commit()

        results = await list_projects(db_session, user.id)
        assert len(results) == 1
        assert results[0]["project_name"] == "visible"

    async def test_list_projects_empty(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """No sessions should return an empty list."""
        results = await list_projects(db_session, user.id)
        assert results == []

    async def test_list_projects_sources(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Verify distinct sources per project."""
        db_session.add(
            _make_session(user.id, 30, project_name="multi", source="claude")
        )
        db_session.add(
            _make_session(user.id, 31, project_name="multi", source="opencode")
        )
        db_session.add(
            _make_session(user.id, 32, project_name="multi", source="claude")
        )
        await db_session.commit()

        results = await list_projects(db_session, user.id)
        assert len(results) == 1
        proj = results[0]
        assert proj["project_name"] == "multi"
        assert proj["session_count"] == 3
        # Sources should be distinct and sorted
        assert proj["sources"] == ["claude", "opencode"]


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestProjectsApi:
    """Tests for the projects API endpoints."""

    async def test_list_projects_api(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """GET /api/projects returns project summaries."""
        db_session.add(
            _make_session(user.id, 40, project_name="api-proj")
        )
        await db_session.commit()

        resp = await client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["project_name"] == "api-proj"
        assert data[0]["session_count"] == 1

    async def test_project_activity_api(self, user: User, engine) -> None:
        """GET /api/projects/activity returns mocked activity data.

        The service uses cast(Date) which doesn't work on SQLite, so
        we mock the service function.
        """
        app = _build_test_app()

        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def _override_db():  # noqa: ANN202
            async with sf() as session:
                yield session

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user

        mock_activity = [
            {"date": "2025-06-01", "project_name": "alpha", "count": 3},
            {"date": "2025-06-01", "project_name": "beta", "count": 1},
            {"date": "2025-06-02", "project_name": "alpha", "count": 2},
        ]

        with patch(
            "src.api.projects.projects_service.get_project_activity",
            new_callable=AsyncMock,
            return_value=mock_activity,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.get("/api/projects/activity?days=30")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["date"] == "2025-06-01"
        assert data[0]["project_name"] == "alpha"
        assert data[0]["count"] == 3
        assert data[2]["date"] == "2025-06-02"

        app.dependency_overrides.clear()
