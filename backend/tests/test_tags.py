"""Tests for the tags service and API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.tags import router as tags_router
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import Base, User
from src.models.session import Session
from src.models.tag import SessionTag
from src.services.tags import (
    add_tag_to_session,
    create_tag,
    delete_tag,
    list_tags,
    remove_tag_from_session,
    update_tag,
)

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
    u = User(id=uuid.uuid4(), email="taguser@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture()
async def sample_session(db_session: AsyncSession, user: User) -> Session:
    """Create a sample session for tag-session association tests."""
    now = datetime.now(timezone.utc)
    s = Session(
        id=uuid.uuid4(),
        user_id=user.id,
        session_key="tag-test-session-0",
        source="claude",
        snapshot_at=now,
        started_at=now,
        last_message_at=now,
        parser_revision=1,
        schema_version=1,
        content_hash="hash-tag-0",
        raw_hash="raw-tag-0",
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


def _build_test_app():
    """Create a minimal FastAPI app with the tags router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(tags_router)
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
# Service tests — create_tag
# ---------------------------------------------------------------------------


class TestCreateTag:
    """Tests for the create_tag service function."""

    async def test_create_tag_success(
        self, db_session: AsyncSession, user: User
    ) -> None:
        result = await create_tag(db_session, user.id, "bugfix", "#ff0000")
        assert result["name"] == "bugfix"
        assert result["color"] == "#ff0000"
        assert result["session_count"] == 0
        assert result["id"] is not None
        assert result["created_at"] is not None

    async def test_create_tag_default_color(
        self, db_session: AsyncSession, user: User
    ) -> None:
        result = await create_tag(db_session, user.id, "feature")
        assert result["color"] == "#6b7280"

    async def test_create_tag_duplicate_name_raises(
        self, db_session: AsyncSession, user: User
    ) -> None:
        await create_tag(db_session, user.id, "duplicate")
        with pytest.raises(ValueError, match="already exists"):
            await create_tag(db_session, user.id, "duplicate")


# ---------------------------------------------------------------------------
# Service tests — list_tags
# ---------------------------------------------------------------------------


class TestListTags:
    """Tests for the list_tags service function."""

    async def test_list_tags_empty(
        self, db_session: AsyncSession, user: User
    ) -> None:
        items = await list_tags(db_session, user.id)
        assert items == []

    async def test_list_tags_returns_all(
        self, db_session: AsyncSession, user: User
    ) -> None:
        await create_tag(db_session, user.id, "alpha", "#111111")
        await create_tag(db_session, user.id, "beta", "#222222")
        await create_tag(db_session, user.id, "gamma", "#333333")

        items = await list_tags(db_session, user.id)
        assert len(items) == 3
        names = [t["name"] for t in items]
        assert names == ["alpha", "beta", "gamma"]  # sorted alphabetically

    async def test_list_tags_with_session_count(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag_result = await create_tag(db_session, user.id, "counted")
        tag_id = uuid.UUID(tag_result["id"])

        # Associate the tag with a session
        await add_tag_to_session(db_session, user.id, sample_session.id, tag_id)

        items = await list_tags(db_session, user.id)
        counted = [t for t in items if t["name"] == "counted"][0]
        assert counted["session_count"] == 1

    async def test_list_tags_isolation(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Tags from one user should not appear for another user."""
        await create_tag(db_session, user.id, "my-tag")

        other_user = User(id=uuid.uuid4(), email="other@example.com")
        db_session.add(other_user)
        await db_session.commit()

        other_items = await list_tags(db_session, other_user.id)
        assert other_items == []


# ---------------------------------------------------------------------------
# Service tests — update_tag
# ---------------------------------------------------------------------------


class TestUpdateTag:
    """Tests for the update_tag service function."""

    async def test_update_tag_name(
        self, db_session: AsyncSession, user: User
    ) -> None:
        tag = await create_tag(db_session, user.id, "old-name")
        tag_id = uuid.UUID(tag["id"])

        result = await update_tag(db_session, user.id, tag_id, name="new-name")
        assert result is not None
        assert result["name"] == "new-name"

    async def test_update_tag_color(
        self, db_session: AsyncSession, user: User
    ) -> None:
        tag = await create_tag(db_session, user.id, "colorful")
        tag_id = uuid.UUID(tag["id"])

        result = await update_tag(db_session, user.id, tag_id, color="#abcdef")
        assert result is not None
        assert result["color"] == "#abcdef"
        assert result["name"] == "colorful"  # unchanged

    async def test_update_tag_duplicate_name_raises(
        self, db_session: AsyncSession, user: User
    ) -> None:
        await create_tag(db_session, user.id, "existing")
        tag = await create_tag(db_session, user.id, "rename-me")
        tag_id = uuid.UUID(tag["id"])

        with pytest.raises(ValueError, match="already exists"):
            await update_tag(db_session, user.id, tag_id, name="existing")

    async def test_update_tag_not_found(
        self, db_session: AsyncSession, user: User
    ) -> None:
        result = await update_tag(db_session, user.id, uuid.uuid4(), name="nope")
        assert result is None

    async def test_update_tag_same_name_no_error(
        self, db_session: AsyncSession, user: User
    ) -> None:
        """Updating a tag to its own current name should succeed."""
        tag = await create_tag(db_session, user.id, "keep-name")
        tag_id = uuid.UUID(tag["id"])

        result = await update_tag(db_session, user.id, tag_id, name="keep-name")
        assert result is not None
        assert result["name"] == "keep-name"


# ---------------------------------------------------------------------------
# Service tests — delete_tag
# ---------------------------------------------------------------------------


class TestDeleteTag:
    """Tests for the delete_tag service function."""

    async def test_delete_tag_success(
        self, db_session: AsyncSession, user: User
    ) -> None:
        tag = await create_tag(db_session, user.id, "to-delete")
        tag_id = uuid.UUID(tag["id"])

        deleted = await delete_tag(db_session, user.id, tag_id)
        assert deleted is True

        # Verify it's gone
        items = await list_tags(db_session, user.id)
        assert len(items) == 0

    async def test_delete_tag_not_found(
        self, db_session: AsyncSession, user: User
    ) -> None:
        deleted = await delete_tag(db_session, user.id, uuid.uuid4())
        assert deleted is False

    async def test_delete_tag_cascades_session_tags(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "cascade-me")
        tag_id = uuid.UUID(tag["id"])
        await add_tag_to_session(db_session, user.id, sample_session.id, tag_id)

        deleted = await delete_tag(db_session, user.id, tag_id)
        assert deleted is True

        # Verify association is also gone
        from sqlalchemy import select

        result = await db_session.execute(
            select(SessionTag).where(SessionTag.tag_id == tag_id)
        )
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Service tests — add/remove tag-session association
# ---------------------------------------------------------------------------


class TestSessionTagAssociation:
    """Tests for add_tag_to_session and remove_tag_from_session."""

    async def test_add_tag_to_session(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "assoc-tag")
        tag_id = uuid.UUID(tag["id"])

        result = await add_tag_to_session(
            db_session, user.id, sample_session.id, tag_id
        )
        assert result is True

    async def test_add_tag_to_session_idempotent(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "idempotent-tag")
        tag_id = uuid.UUID(tag["id"])

        await add_tag_to_session(db_session, user.id, sample_session.id, tag_id)
        result = await add_tag_to_session(
            db_session, user.id, sample_session.id, tag_id
        )
        assert result is True  # No error, idempotent

    async def test_add_tag_wrong_user(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "wrong-user-tag")
        tag_id = uuid.UUID(tag["id"])

        other_user_id = uuid.uuid4()
        result = await add_tag_to_session(
            db_session, other_user_id, sample_session.id, tag_id
        )
        assert result is False

    async def test_remove_tag_from_session(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "remove-tag")
        tag_id = uuid.UUID(tag["id"])

        await add_tag_to_session(db_session, user.id, sample_session.id, tag_id)
        result = await remove_tag_from_session(
            db_session, user.id, sample_session.id, tag_id
        )
        assert result is True

    async def test_remove_nonexistent_association(
        self, db_session: AsyncSession, user: User, sample_session: Session
    ) -> None:
        tag = await create_tag(db_session, user.id, "no-assoc-tag")
        tag_id = uuid.UUID(tag["id"])

        result = await remove_tag_from_session(
            db_session, user.id, sample_session.id, tag_id
        )
        assert result is False


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestTagApiRoutes:
    """Tests for the tag CRUD API endpoints."""

    async def test_api_create_tag(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/tags", json={"name": "api-tag", "color": "#00ff00"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "api-tag"
        assert data["color"] == "#00ff00"
        assert data["session_count"] == 0
        assert "id" in data

    async def test_api_create_tag_default_color(self, client: AsyncClient) -> None:
        resp = await client.post("/api/tags", json={"name": "default-color"})
        assert resp.status_code == 201
        assert resp.json()["color"] == "#6b7280"

    async def test_api_create_tag_duplicate_409(self, client: AsyncClient) -> None:
        await client.post("/api/tags", json={"name": "dup-tag"})
        resp = await client.post("/api/tags", json={"name": "dup-tag"})
        assert resp.status_code == 409

    async def test_api_create_tag_invalid_color(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/tags", json={"name": "bad-color", "color": "not-a-color"}
        )
        assert resp.status_code == 422

    async def test_api_create_tag_empty_name(self, client: AsyncClient) -> None:
        resp = await client.post("/api/tags", json={"name": ""})
        assert resp.status_code == 422

    async def test_api_create_tag_long_name(self, client: AsyncClient) -> None:
        resp = await client.post("/api/tags", json={"name": "a" * 51})
        assert resp.status_code == 422

    async def test_api_list_tags(self, client: AsyncClient) -> None:
        await client.post("/api/tags", json={"name": "list-a"})
        await client.post("/api/tags", json={"name": "list-b"})

        resp = await client.get("/api/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [t["name"] for t in data]
        assert "list-a" in names
        assert "list-b" in names

    async def test_api_list_tags_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_api_update_tag_name(self, client: AsyncClient) -> None:
        create_resp = await client.post("/api/tags", json={"name": "old-api-name"})
        tag_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/tags/{tag_id}", json={"name": "new-api-name"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "new-api-name"

    async def test_api_update_tag_color(self, client: AsyncClient) -> None:
        create_resp = await client.post("/api/tags", json={"name": "update-color"})
        tag_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/tags/{tag_id}", json={"color": "#abcdef"}
        )
        assert resp.status_code == 200
        assert resp.json()["color"] == "#abcdef"

    async def test_api_update_tag_not_found(self, client: AsyncClient) -> None:
        random_id = uuid.uuid4()
        resp = await client.patch(
            f"/api/tags/{random_id}", json={"name": "nope"}
        )
        assert resp.status_code == 404

    async def test_api_update_tag_duplicate_name_409(
        self, client: AsyncClient
    ) -> None:
        await client.post("/api/tags", json={"name": "existing-name"})
        create_resp = await client.post("/api/tags", json={"name": "rename-this"})
        tag_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/tags/{tag_id}", json={"name": "existing-name"}
        )
        assert resp.status_code == 409

    async def test_api_delete_tag(self, client: AsyncClient) -> None:
        create_resp = await client.post("/api/tags", json={"name": "to-delete-api"})
        tag_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/tags/{tag_id}")
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = await client.get("/api/tags")
        assert len(list_resp.json()) == 0

    async def test_api_delete_tag_not_found(self, client: AsyncClient) -> None:
        random_id = uuid.uuid4()
        resp = await client.delete(f"/api/tags/{random_id}")
        assert resp.status_code == 404
