"""Tests for Azure Blob Storage service."""
from __future__ import annotations

from src.services.storage import BlobStorageService

# ---------------------------------------------------------------------------
# Key construction tests (no Azure connection needed)
# ---------------------------------------------------------------------------


class TestCanonicalKeyFormat:
    """Tests for canonical blob key construction."""

    def test_canonical_key_format(self) -> None:
        """Canonical key follows {user_id}/{session_key}/canonical.json.gz pattern."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key = svc._canonical_key("user-123", "sess-abc")
        assert key == "user-123/sess-abc/canonical.json.gz"

    def test_canonical_key_with_uuid_style_ids(self) -> None:
        """Canonical key works with UUID-style identifiers."""
        svc = BlobStorageService.__new__(BlobStorageService)
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        session_key = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
        key = svc._canonical_key(user_id, session_key)
        assert key == f"{user_id}/{session_key}/canonical.json.gz"

    def test_canonical_key_ends_with_gz(self) -> None:
        """Canonical key must end with .json.gz extension."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key = svc._canonical_key("u", "s")
        assert key.endswith(".json.gz")


class TestRawKeyFormat:
    """Tests for raw blob key construction."""

    def test_raw_key_format(self) -> None:
        """Raw key follows {user_id}/{session_key}/raw/{raw_hash}.json.gz pattern."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key = svc._raw_key("user-123", "sess-abc", "deadbeef")
        assert key == "user-123/sess-abc/raw/deadbeef.json.gz"

    def test_raw_key_with_sha256_hash(self) -> None:
        """Raw key works with full SHA-256 hex digest."""
        svc = BlobStorageService.__new__(BlobStorageService)
        raw_hash = "a" * 64  # SHA-256 hex length
        key = svc._raw_key("user-1", "sess-1", raw_hash)
        assert key == f"user-1/sess-1/raw/{raw_hash}.json.gz"

    def test_raw_key_ends_with_gz(self) -> None:
        """Raw key must end with .json.gz extension."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key = svc._raw_key("u", "s", "h")
        assert key.endswith(".json.gz")

    def test_raw_key_contains_raw_directory(self) -> None:
        """Raw key must include /raw/ path segment."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key = svc._raw_key("u", "s", "h")
        assert "/raw/" in key


class TestKeyConstruction:
    """Cross-cutting key construction tests."""

    def test_canonical_and_raw_keys_share_prefix(self) -> None:
        """Canonical and raw keys for the same session share the user/session prefix."""
        svc = BlobStorageService.__new__(BlobStorageService)
        canonical = svc._canonical_key("user-1", "sess-1")
        raw = svc._raw_key("user-1", "sess-1", "hash123")
        prefix = "user-1/sess-1/"
        assert canonical.startswith(prefix)
        assert raw.startswith(prefix)

    def test_raw_keys_differ_by_hash(self) -> None:
        """Different raw_hash values produce different keys."""
        svc = BlobStorageService.__new__(BlobStorageService)
        key1 = svc._raw_key("u", "s", "hash1")
        key2 = svc._raw_key("u", "s", "hash2")
        assert key1 != key2

    def test_keys_use_forward_slashes(self) -> None:
        """All keys use forward slashes as path separators."""
        svc = BlobStorageService.__new__(BlobStorageService)
        canonical = svc._canonical_key("user-1", "sess-1")
        raw = svc._raw_key("user-1", "sess-1", "h")
        assert "\\" not in canonical
        assert "\\" not in raw


# ---------------------------------------------------------------------------
# Service instantiation tests
# ---------------------------------------------------------------------------


class TestBlobStorageServiceInit:
    """Tests for BlobStorageService constructor."""

    def test_stores_container_name(self) -> None:
        """Constructor stores the container name."""
        svc = BlobStorageService(
            connection_string="DefaultEndpointsProtocol=http;AccountName=test",
            container_name="my-container",
        )
        assert svc._container_name == "my-container"

    def test_stores_connection_string(self) -> None:
        """Constructor stores the connection string."""
        conn = "DefaultEndpointsProtocol=http;AccountName=test"
        svc = BlobStorageService(
            connection_string=conn,
            container_name="sessions",
        )
        assert svc._connection_string == conn


# ---------------------------------------------------------------------------
# FastAPI dependency tests
# ---------------------------------------------------------------------------


class TestGetStorageService:
    """Tests for the get_storage_service FastAPI dependency."""

    def test_returns_blob_storage_service(self) -> None:
        """get_storage_service returns a BlobStorageService instance."""
        from src.services.storage import get_storage_service

        svc = get_storage_service()
        assert isinstance(svc, BlobStorageService)

    def test_returns_same_singleton(self) -> None:
        """get_storage_service returns the same instance on repeated calls."""
        from src.services.storage import get_storage_service

        svc1 = get_storage_service()
        svc2 = get_storage_service()
        assert svc1 is svc2


# ---------------------------------------------------------------------------
# Async method signature tests (verify interface exists)
# ---------------------------------------------------------------------------


class TestAsyncMethodSignatures:
    """Verify async methods exist with correct signatures (no actual I/O)."""

    def test_upload_canonical_is_coroutine(self) -> None:
        """upload_canonical must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.upload_canonical("u", "s", b"data")
        assert asyncio.iscoroutine(result)
        result.close()  # prevent RuntimeWarning

    def test_upload_raw_is_coroutine(self) -> None:
        """upload_raw must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.upload_raw("u", "s", "h", b"data")
        assert asyncio.iscoroutine(result)
        result.close()

    def test_download_is_coroutine(self) -> None:
        """download must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.download("key")
        assert asyncio.iscoroutine(result)
        result.close()

    def test_exists_is_coroutine(self) -> None:
        """exists must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.exists("key")
        assert asyncio.iscoroutine(result)
        result.close()

    def test_generate_sas_url_is_coroutine(self) -> None:
        """generate_sas_url must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.generate_sas_url("key")
        assert asyncio.iscoroutine(result)
        result.close()

    def test_get_blob_size_is_coroutine(self) -> None:
        """get_blob_size must be an async method."""
        import asyncio

        svc = BlobStorageService.__new__(BlobStorageService)
        result = svc.get_blob_size("key")
        assert asyncio.iscoroutine(result)
        result.close()
