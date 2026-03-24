"""Tests for the sessions service and API routes (Phase 3a read APIs)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.sessions import router as sessions_router
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import Base, User
from src.models.session import Message, MessageChunk, Session
from src.services.sessions import (
    get_session_detail,
    get_session_filters,
    list_sessions,
)

# ---------------------------------------------------------------------------
# BFF proxy auth header — matches config default
# ---------------------------------------------------------------------------
BFF_SECRET = "dev-backend-secret-change-in-production"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine():
    """Create a SQLite async engine and provision all tables.

    PostgreSQL-specific column types (UUID, TSVECTOR, BIGINT) are compiled as
    TEXT / INTEGER by SQLAlchemy's generic type fallback or by the compile-time
    listener registered below.
    """
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)

    # SQLite doesn't understand TSVECTOR – compile it as TEXT.
    from sqlalchemy.dialects.postgresql import TSVECTOR

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001,ANN202
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        # Register a custom type compiler so TSVECTOR renders as TEXT in DDL.
        from sqlalchemy.ext.compiler import compiles

        @compiles(TSVECTOR, "sqlite")
        def _compile_tsvector(element, compiler, **kw):  # noqa: ANN001,ANN202
            return "TEXT"

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
    u = User(id=uuid.uuid4(), email="testuser@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture()
async def sample_sessions(db_session: AsyncSession, user: User) -> list[Session]:
    """Create 5 sessions with varied sources, projects, and models."""
    now = datetime.now(timezone.utc)
    configs = [
        {
            "source": "claude",
            "project_name": "project-alpha",
            "model": "claude-3.5-sonnet",
            "started_at": now - timedelta(days=5),
            "total_messages": 10,
        },
        {
            "source": "claude",
            "project_name": "project-alpha",
            "model": "claude-3.5-sonnet",
            "started_at": now - timedelta(days=4),
            "total_messages": 20,
        },
        {
            "source": "opencode",
            "project_name": "project-beta",
            "model": "gpt-4o",
            "started_at": now - timedelta(days=3),
            "total_messages": 15,
        },
        {
            "source": "gemini",
            "project_name": "project-beta",
            "model": "gemini-2.0-flash",
            "started_at": now - timedelta(days=2),
            "total_messages": 5,
        },
        {
            "source": "opencode",
            "project_name": None,
            "model": None,
            "started_at": now - timedelta(days=1),
            "total_messages": 8,
        },
    ]

    sessions: list[Session] = []
    for i, cfg in enumerate(configs):
        s = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            session_key=f"session-{i}",
            source=cfg["source"],
            project_name=cfg["project_name"],
            model=cfg["model"],
            started_at=cfg["started_at"],
            last_message_at=cfg["started_at"],
            snapshot_at=now,
            total_messages=cfg["total_messages"],
            user_messages=cfg["total_messages"] // 2,
            assistant_messages=cfg["total_messages"] // 2,
            total_input_tokens=100 * (i + 1),
            total_output_tokens=200 * (i + 1),
            total_cached_tokens=0,
            parser_revision=1,
            schema_version=1,
            content_hash=f"hash-{i}",
            raw_hash=f"raw-{i}",
        )
        db_session.add(s)
        sessions.append(s)

    await db_session.commit()
    for s in sessions:
        await db_session.refresh(s)
    return sessions


def _build_test_app():
    """Create a minimal FastAPI app with the sessions router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(sessions_router)
    return test_app


@pytest.fixture()
async def client(db_session: AsyncSession, user: User, engine):
    """Yield an httpx AsyncClient wired to the test app with SQLite DB."""
    app = _build_test_app()

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
# Service tests — list_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    """Tests for the list_sessions service function."""

    async def test_list_sessions_returns_all(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        items, total = await list_sessions(db_session, user.id)
        assert total == 5
        assert len(items) == 5

    async def test_list_sessions_filter_by_source(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        items, total = await list_sessions(db_session, user.id, source="claude")
        assert total == 2
        assert all(s.source == "claude" for s in items)

    async def test_list_sessions_filter_by_project(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        items, total = await list_sessions(db_session, user.id, project="project-beta")
        assert total == 2
        assert all(s.project_name == "project-beta" for s in items)

    async def test_list_sessions_pagination(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        items, total = await list_sessions(db_session, user.id, page=1, page_size=2)
        assert len(items) == 2
        assert total == 5
        # has_more is the caller's responsibility, but total > page*page_size
        assert total > 1 * 2

    async def test_list_sessions_excludes_deleted(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        # Soft-delete one session
        sample_sessions[0].deleted_at = datetime.now(timezone.utc)
        await db_session.commit()

        items, total = await list_sessions(db_session, user.id)
        assert total == 4
        deleted_ids = {s.id for s in items}
        assert sample_sessions[0].id not in deleted_ids

    async def test_list_sessions_sort_order_asc(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        items, _ = await list_sessions(
            db_session, user.id, sort_by="started_at", sort_order="asc"
        )
        dates = [s.started_at for s in items if s.started_at is not None]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Service tests — get_session_detail
# ---------------------------------------------------------------------------


class TestGetSessionDetail:
    """Tests for the get_session_detail service function."""

    async def test_get_session_detail_with_messages(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        session = sample_sessions[0]

        # Create messages with chunks
        msg1 = Message(
            id=uuid.uuid4(),
            session_id=session.id,
            role="user",
            ordinal=0,
            input_tokens=50,
            output_tokens=0,
        )
        msg2 = Message(
            id=uuid.uuid4(),
            session_id=session.id,
            role="assistant",
            ordinal=1,
            input_tokens=0,
            output_tokens=150,
        )
        db_session.add_all([msg1, msg2])
        await db_session.flush()

        # Create chunks — split a message across 2 chunks
        chunk1 = MessageChunk(
            id=uuid.uuid4(),
            message_id=msg1.id,
            session_id=session.id,
            chunk_index=0,
            content="Hello, ",
        )
        chunk2 = MessageChunk(
            id=uuid.uuid4(),
            message_id=msg1.id,
            session_id=session.id,
            chunk_index=1,
            content="world!",
        )
        chunk3 = MessageChunk(
            id=uuid.uuid4(),
            message_id=msg2.id,
            session_id=session.id,
            chunk_index=0,
            content="Hi there!",
        )
        db_session.add_all([chunk1, chunk2, chunk3])
        await db_session.commit()

        detail = await get_session_detail(db_session, user.id, session.id)
        assert detail is not None
        assert detail.session.id == session.id
        assert len(detail.messages) == 2

        # Verify chunk assembly
        assert detail.messages[0].content == "Hello, world!"
        assert detail.messages[0].role == "user"
        assert detail.messages[1].content == "Hi there!"
        assert detail.messages[1].role == "assistant"

    async def test_get_session_detail_not_found(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        # Use a different user_id — should not find anything
        other_user_id = uuid.uuid4()
        detail = await get_session_detail(
            db_session, other_user_id, sample_sessions[0].id
        )
        assert detail is None

    async def test_get_session_detail_nonexistent_session(
        self, db_session: AsyncSession, user: User
    ) -> None:
        detail = await get_session_detail(db_session, user.id, uuid.uuid4())
        assert detail is None


# ---------------------------------------------------------------------------
# Service tests — get_session_filters
# ---------------------------------------------------------------------------


class TestGetSessionFilters:
    """Tests for the get_session_filters service function."""

    async def test_get_session_filters(
        self, db_session: AsyncSession, user: User, sample_sessions: list[Session]
    ) -> None:
        fv = await get_session_filters(db_session, user.id)
        assert sorted(fv.sources) == ["claude", "gemini", "opencode"]
        assert sorted(fv.projects) == ["project-alpha", "project-beta"]
        # model=None sessions are excluded from the models list
        assert sorted(fv.models) == ["claude-3.5-sonnet", "gemini-2.0-flash", "gpt-4o"]


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestSessionApiRoutes:
    """Tests for the session read API endpoints."""

    async def test_api_list_sessions(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert "has_more" in data

    async def test_api_session_detail(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user: User,
        sample_sessions: list[Session],
        engine,
    ) -> None:
        session = sample_sessions[0]

        # Add a message + chunk via a fresh DB session
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as fresh_db:
            msg = Message(
                id=uuid.uuid4(),
                session_id=session.id,
                role="user",
                ordinal=0,
                input_tokens=10,
                output_tokens=0,
            )
            fresh_db.add(msg)
            await fresh_db.flush()
            chunk = MessageChunk(
                id=uuid.uuid4(),
                message_id=msg.id,
                session_id=session.id,
                chunk_index=0,
                content="Test content",
            )
            fresh_db.add(chunk)
            await fresh_db.commit()

        resp = await client.get(f"/api/sessions/{session.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(session.id)
        assert "messages" in data
        assert len(data["messages"]) >= 1
        assert data["messages"][0]["content"] == "Test content"

    async def test_api_session_detail_404(self, client: AsyncClient) -> None:
        random_id = uuid.uuid4()
        resp = await client.get(f"/api/sessions/{random_id}")
        assert resp.status_code == 404

    async def test_api_session_filters(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        resp = await client.get("/api/sessions/filters")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "projects" in data
        assert "models" in data
        assert sorted(data["sources"]) == ["claude", "gemini", "opencode"]

    async def test_api_list_sessions_with_source_filter(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        resp = await client.get("/api/sessions", params={"source": "claude"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(item["source"] == "claude" for item in data["items"])

    async def test_api_list_sessions_pagination(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        resp = await client.get(
            "/api/sessions", params={"page": 1, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True


class TestSessionApiAuth:
    """Test that session endpoints reject unauthenticated requests."""

    async def test_api_list_sessions_unauthorized(self) -> None:
        """Requests without auth headers should be rejected with 401."""
        from fastapi import FastAPI

        # Build app WITHOUT the auth override so real dependency runs
        app = FastAPI()
        app.include_router(sessions_router)

        # Override get_db to provide a mock DB that returns None for user lookups
        from unittest.mock import AsyncMock, MagicMock

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
            resp = await ac.get("/api/sessions")
        assert resp.status_code == 401
        app.dependency_overrides.clear()
