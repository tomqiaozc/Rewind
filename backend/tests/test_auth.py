"""Tests for the dual auth system (BFF proxy + API key)."""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.auth.api_key import generate_api_key, hash_api_key
from src.auth.dependencies import get_current_user
from src.db.session import get_db
from src.models.base import ApiKey, User

# ---------------------------------------------------------------------------
# Unit tests for api_key module
# ---------------------------------------------------------------------------


class TestGenerateApiKey:
    """Tests for generate_api_key()."""

    def test_starts_with_rw_prefix(self) -> None:
        key = generate_api_key()
        assert key.startswith("rw_")

    def test_has_correct_length(self) -> None:
        # "rw_" (3 chars) + 32 hex chars = 35 total
        key = generate_api_key()
        assert len(key) == 35

    def test_generates_unique_keys(self) -> None:
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_hex_suffix_is_valid_hex(self) -> None:
        key = generate_api_key()
        hex_part = key[3:]
        # Should not raise
        int(hex_part, 16)


class TestHashApiKey:
    """Tests for hash_api_key()."""

    def test_returns_sha256_hex_digest(self) -> None:
        key = "rw_abc123"
        result = hash_api_key(key)
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert result == expected

    def test_consistent_hashing(self) -> None:
        key = generate_api_key()
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_keys_produce_different_hashes(self) -> None:
        k1 = generate_api_key()
        k2 = generate_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------


def _make_mock_db(scalar_return: object = None) -> AsyncMock:
    """Create a mock AsyncSession where execute().scalar_one_or_none()
    returns *scalar_return*.

    SQLAlchemy's Result.scalar_one_or_none() is synchronous, so we use a
    MagicMock for the result and an AsyncMock only for the async execute().
    """
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = scalar_return
    db.execute.return_value = result_mock
    return db


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with the auth dependency wired in."""
    test_app = FastAPI()

    @test_app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/api/protected")
    async def protected(
        user: User = Depends(get_current_user),  # noqa: B008
    ) -> dict[str, str]:
        return {"user_id": str(user.id), "email": user.email}

    return test_app


# ---------------------------------------------------------------------------
# Integration tests for auth dependencies via the FastAPI test client
# ---------------------------------------------------------------------------


class TestHealthEndpointNoAuth:
    """Health endpoint must be accessible without any auth."""

    def test_health_no_auth(self) -> None:
        app = _make_test_app()
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestProtectedEndpointRejectsUnauthenticated:
    """Protected endpoint must reject requests with no valid auth."""

    def test_no_headers_returns_401(self) -> None:
        app = _make_test_app()

        async def mock_get_db():  # noqa: ANN202
            yield _make_mock_db(scalar_return=None)

        app.dependency_overrides[get_db] = mock_get_db
        client = TestClient(app)
        resp = client.get("/api/protected")
        assert resp.status_code == 401
        app.dependency_overrides.clear()

    def test_invalid_api_key_returns_401(self) -> None:
        app = _make_test_app()

        async def mock_get_db():  # noqa: ANN202
            yield _make_mock_db(scalar_return=None)

        app.dependency_overrides[get_db] = mock_get_db
        client = TestClient(app)
        resp = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer rw_invalidkey000000000000000000000"},
        )
        assert resp.status_code == 401
        app.dependency_overrides.clear()

    def test_wrong_backend_secret_returns_401(self) -> None:
        app = _make_test_app()

        async def mock_get_db():  # noqa: ANN202
            yield _make_mock_db(scalar_return=None)

        app.dependency_overrides[get_db] = mock_get_db
        client = TestClient(app)
        resp = client.get(
            "/api/protected",
            headers={
                "X-Backend-Secret": "wrong-secret",
                "X-User-Id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 401
        app.dependency_overrides.clear()


class TestBffProxyAuth:
    """Test BFF proxy auth path (X-Backend-Secret + X-User-Id)."""

    def test_valid_bff_headers_returns_user(self) -> None:
        user_id = uuid.uuid4()
        mock_user = User(id=user_id, email="test@example.com")

        app = _make_test_app()

        async def mock_get_db():  # noqa: ANN202
            yield _make_mock_db(scalar_return=mock_user)

        app.dependency_overrides[get_db] = mock_get_db

        client = TestClient(app)
        with patch("src.auth.dependencies.settings") as mock_settings:
            mock_settings.backend_secret = "test-secret"
            resp = client.get(
                "/api/protected",
                headers={
                    "X-Backend-Secret": "test-secret",
                    "X-User-Id": str(user_id),
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(user_id)
        assert data["email"] == "test@example.com"
        app.dependency_overrides.clear()


class TestApiKeyAuth:
    """Test API key auth path (Bearer rw_...)."""

    def test_valid_api_key_returns_user(self) -> None:
        user_id = uuid.uuid4()
        mock_user = User(id=user_id, email="cli@example.com")
        raw_key = "rw_" + "a" * 32
        key_hash = hash_api_key(raw_key)
        mock_api_key = ApiKey(
            id=uuid.uuid4(),
            user_id=user_id,
            key_hash=key_hash,
        )
        mock_api_key.user = mock_user  # type: ignore[assignment]

        app = _make_test_app()

        async def mock_get_db():  # noqa: ANN202
            yield _make_mock_db(scalar_return=mock_api_key)

        app.dependency_overrides[get_db] = mock_get_db

        client = TestClient(app)
        resp = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(user_id)
        assert data["email"] == "cli@example.com"
        app.dependency_overrides.clear()
