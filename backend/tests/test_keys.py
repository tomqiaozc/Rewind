"""Tests for API key management endpoints (list + delete)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.keys import router as keys_router
from src.auth.api_key import hash_api_key
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import ApiKey, Base, User

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
    u = User(id=uuid.uuid4(), email="keyuser@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


def _build_test_app():
    """Create a minimal FastAPI app with the keys router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(keys_router)
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _create_api_key(
    db_session: AsyncSession,
    user: User,
    device_name: str = "test-device",
    prefix: str = "rw_abc12",
) -> ApiKey:
    """Helper to create an API key directly in the DB."""
    key = ApiKey(
        id=uuid.uuid4(),
        user_id=user.id,
        key_hash=hash_api_key("rw_" + uuid.uuid4().hex[:32]),
        key_prefix=prefix,
        device_name=device_name,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    return key


# ---------------------------------------------------------------------------
# API route tests — GET /api/keys
# ---------------------------------------------------------------------------


class TestListKeys:
    """Tests for GET /api/keys."""

    async def test_list_keys_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/keys")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_keys_returns_all(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        await _create_api_key(db_session, user, device_name="device-a", prefix="rw_aaaa")
        await _create_api_key(db_session, user, device_name="device-b", prefix="rw_bbbb")

        resp = await client.get("/api/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        device_names = {k["device_name"] for k in data}
        assert device_names == {"device-a", "device-b"}

    async def test_list_keys_returns_expected_fields(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        await _create_api_key(db_session, user, device_name="my-laptop", prefix="rw_test1")

        resp = await client.get("/api/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        key = data[0]
        assert "id" in key
        assert key["device_name"] == "my-laptop"
        assert key["key_prefix"] == "rw_test1"
        assert "created_at" in key
        assert "last_used_at" in key
        # Must NOT expose key_hash or the full key
        assert "key_hash" not in key
        assert "key" not in key

    async def test_list_keys_isolation(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Keys from another user should not appear."""
        other_user = User(id=uuid.uuid4(), email="other@example.com")
        db_session.add(other_user)
        await db_session.commit()

        await _create_api_key(db_session, other_user, device_name="other-device")

        resp = await client.get("/api/keys")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_keys_ordered_by_created_at_desc(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        k1 = await _create_api_key(db_session, user, device_name="first")  # noqa: F841
        k2 = await _create_api_key(db_session, user, device_name="second")  # noqa: F841

        resp = await client.get("/api/keys")
        data = resp.json()
        # Most recent first
        assert data[0]["device_name"] == "second"
        assert data[1]["device_name"] == "first"


# ---------------------------------------------------------------------------
# API route tests — DELETE /api/keys/{id}
# ---------------------------------------------------------------------------


class TestDeleteKey:
    """Tests for DELETE /api/keys/{id}."""

    async def test_delete_key_success(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        key = await _create_api_key(db_session, user)

        resp = await client.delete(f"/api/keys/{key.id}")
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = await client.get("/api/keys")
        assert list_resp.json() == []

    async def test_delete_key_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete(f"/api/keys/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_delete_key_owned_by_other_user(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Cannot delete another user's key."""
        other_user = User(id=uuid.uuid4(), email="other2@example.com")
        db_session.add(other_user)
        await db_session.commit()

        key = await _create_api_key(db_session, other_user, device_name="other-key")

        resp = await client.delete(f"/api/keys/{key.id}")
        assert resp.status_code == 404

    async def test_delete_key_invalid_uuid(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/keys/not-a-uuid")
        assert resp.status_code == 422

    async def test_delete_key_then_list_reflects_removal(
        self, client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """After deleting one of two keys, only one remains."""
        k1 = await _create_api_key(db_session, user, device_name="keep-me")  # noqa: F841
        k2 = await _create_api_key(db_session, user, device_name="delete-me")

        await client.delete(f"/api/keys/{k2.id}")

        list_resp = await client.get("/api/keys")
        data = list_resp.json()
        assert len(data) == 1
        assert data[0]["device_name"] == "keep-me"


# ---------------------------------------------------------------------------
# Auth tests — unauthenticated access
# ---------------------------------------------------------------------------


class TestKeysApiAuth:
    """Test that key endpoints reject unauthenticated requests."""

    async def test_list_keys_unauthorized(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(keys_router)

        async def _mock_db():  # noqa: ANN202
            mock = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock.execute.return_value = result_mock
            yield mock

        app.dependency_overrides[get_db] = _mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/keys")
        assert resp.status_code == 401
        app.dependency_overrides.clear()

    async def test_delete_key_unauthorized(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(keys_router)

        async def _mock_db():  # noqa: ANN202
            mock = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            mock.execute.return_value = result_mock
            yield mock

        app.dependency_overrides[get_db] = _mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/keys/{uuid.uuid4()}")
        assert resp.status_code == 401
        app.dependency_overrides.clear()
