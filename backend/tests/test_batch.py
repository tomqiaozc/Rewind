"""Tests for star, trash, restore, batch operations, and session-tag APIs."""

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
from src.models.session import Session
from src.models.tag import Tag

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine():
    """Create a SQLite async engine and provision all tables."""
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)

    from sqlalchemy.dialects.postgresql import TSVECTOR

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001,ANN202
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # Register a dummy to_tsvector so the GENERATED column DDL succeeds.
        dbapi_conn.create_function("to_tsvector", 2, lambda *args: "", deterministic=True)

    async with eng.begin() as conn:
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
    u = User(id=uuid.uuid4(), email="batchuser@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture()
async def sample_sessions(db_session: AsyncSession, user: User) -> list[Session]:
    """Create 3 sessions for testing."""
    now = datetime.now(timezone.utc)
    sessions_list: list[Session] = []
    for i in range(3):
        s = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            session_key=f"batch-session-{i}",
            source="claude",
            started_at=now - timedelta(days=i),
            last_message_at=now - timedelta(days=i),
            snapshot_at=now,
            total_messages=10,
            user_messages=5,
            assistant_messages=5,
            total_input_tokens=100,
            total_output_tokens=200,
            total_cached_tokens=0,
            parser_revision=1,
            schema_version=1,
            content_hash=f"hash-batch-{i}",
            raw_hash=f"raw-batch-{i}",
        )
        db_session.add(s)
        sessions_list.append(s)
    await db_session.commit()
    for s in sessions_list:
        await db_session.refresh(s)
    return sessions_list


@pytest.fixture()
async def sample_tag(db_session: AsyncSession, user: User) -> Tag:
    """Create a tag for testing session-tag association."""
    t = Tag(
        id=uuid.uuid4(),
        user_id=user.id,
        name="test-tag",
        color="#ff0000",
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Star tests
# ---------------------------------------------------------------------------


class TestStarSession:
    async def test_star_session(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        session_id = sample_sessions[0].id
        resp = await client.patch(
            f"/api/sessions/{session_id}/star",
            json={"is_starred": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_starred"] is True

    async def test_unstar_session(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        session_id = sample_sessions[0].id
        # Star first
        await client.patch(
            f"/api/sessions/{session_id}/star",
            json={"is_starred": True},
        )
        # Then unstar
        resp = await client.patch(
            f"/api/sessions/{session_id}/star",
            json={"is_starred": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_starred"] is False

    async def test_star_nonexistent(self, client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        resp = await client.patch(
            f"/api/sessions/{fake_id}/star",
            json={"is_starred": True},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Trash / Restore tests
# ---------------------------------------------------------------------------


class TestTrashRestore:
    async def test_trash_session(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        session_id = sample_sessions[0].id
        resp = await client.post(f"/api/sessions/{session_id}/trash")
        assert resp.status_code == 204

        # Session should be excluded from normal list
        list_resp = await client.get("/api/sessions")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert str(session_id) not in ids

    async def test_trash_already_trashed(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        session_id = sample_sessions[0].id
        await client.post(f"/api/sessions/{session_id}/trash")
        # Trash again — should 404
        resp = await client.post(f"/api/sessions/{session_id}/trash")
        assert resp.status_code == 404

    async def test_restore_session(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        session_id = sample_sessions[0].id
        await client.post(f"/api/sessions/{session_id}/trash")

        resp = await client.delete(f"/api/sessions/{session_id}/trash")
        assert resp.status_code == 204

        # Session should be back in normal list
        list_resp = await client.get("/api/sessions")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert str(session_id) in ids

    async def test_restore_not_trashed(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        session_id = sample_sessions[0].id
        # Not trashed — should 404
        resp = await client.delete(f"/api/sessions/{session_id}/trash")
        assert resp.status_code == 404

    async def test_list_trash(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        # Trash two sessions
        await client.post(f"/api/sessions/{sample_sessions[0].id}/trash")
        await client.post(f"/api/sessions/{sample_sessions[1].id}/trash")

        resp = await client.get("/api/sessions/trash")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Only trashed sessions appear
        trashed_ids = {item["id"] for item in data["items"]}
        assert str(sample_sessions[0].id) in trashed_ids
        assert str(sample_sessions[1].id) in trashed_ids
        assert str(sample_sessions[2].id) not in trashed_ids


# ---------------------------------------------------------------------------
# Batch tests
# ---------------------------------------------------------------------------


class TestBatchOperation:
    async def test_batch_star(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        ids = [str(s.id) for s in sample_sessions[:2]]
        resp = await client.post(
            "/api/sessions/batch",
            json={"session_ids": ids, "action": "star"},
        )
        assert resp.status_code == 200
        assert resp.json()["affected"] == 2

    async def test_batch_trash(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        ids = [str(s.id) for s in sample_sessions]
        resp = await client.post(
            "/api/sessions/batch",
            json={"session_ids": ids, "action": "trash"},
        )
        assert resp.status_code == 200
        assert resp.json()["affected"] == 3

        # Verify they're excluded from normal list
        list_resp = await client.get("/api/sessions")
        assert list_resp.json()["total"] == 0

    async def test_batch_restore(self, client: AsyncClient, sample_sessions: list[Session]) -> None:
        ids = [str(s.id) for s in sample_sessions[:2]]
        # Trash first
        await client.post(
            "/api/sessions/batch",
            json={"session_ids": ids, "action": "trash"},
        )
        # Restore
        resp = await client.post(
            "/api/sessions/batch",
            json={"session_ids": ids, "action": "restore"},
        )
        assert resp.status_code == 200
        assert resp.json()["affected"] == 2

    async def test_batch_invalid_action(
        self, client: AsyncClient, sample_sessions: list[Session]
    ) -> None:
        ids = [str(s.id) for s in sample_sessions[:1]]
        resp = await client.post(
            "/api/sessions/batch",
            json={"session_ids": ids, "action": "delete_forever"},
        )
        assert resp.status_code == 422  # Pydantic validation rejects unknown action


# ---------------------------------------------------------------------------
# Tag association tests
# ---------------------------------------------------------------------------


class TestTagAssociation:
    async def test_add_tag_to_session_via_api(
        self,
        client: AsyncClient,
        sample_sessions: list[Session],
        sample_tag: Tag,
    ) -> None:
        session_id = sample_sessions[0].id
        resp = await client.put(f"/api/sessions/{session_id}/tags/{sample_tag.id}")
        assert resp.status_code == 204

    async def test_remove_tag_from_session_via_api(
        self,
        client: AsyncClient,
        sample_sessions: list[Session],
        sample_tag: Tag,
    ) -> None:
        session_id = sample_sessions[0].id
        # Add first
        await client.put(f"/api/sessions/{session_id}/tags/{sample_tag.id}")
        # Remove
        resp = await client.delete(f"/api/sessions/{session_id}/tags/{sample_tag.id}")
        assert resp.status_code == 204

    async def test_add_tag_nonexistent(
        self,
        client: AsyncClient,
        sample_sessions: list[Session],
    ) -> None:
        session_id = sample_sessions[0].id
        fake_tag_id = uuid.uuid4()
        resp = await client.put(f"/api/sessions/{session_id}/tags/{fake_tag_id}")
        assert resp.status_code == 404
