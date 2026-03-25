"""Tests for upload engine."""
from __future__ import annotations

import gzip
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.upload.content import compress_json
from src.upload.engine import UploadEngine


def test_compress_json() -> None:
    data = {"hello": "world", "messages": [1, 2, 3]}
    compressed = compress_json(data)
    # Verify it's valid gzip
    decompressed = gzip.decompress(compressed)
    assert json.loads(decompressed) == data


def test_compress_json_large() -> None:
    data = {"content": "x" * 100_000}
    compressed = compress_json(data)
    assert len(compressed) < len(json.dumps(data).encode())


@pytest.mark.asyncio
async def test_upload_engine_batch_metadata() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ingested": 2, "skipped": 0}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response

    engine = UploadEngine(client=mock_client, api_url="https://api.example.com")

    sessions: list[dict[str, Any]] = [
        {
            "session_key": "s1",
            "source": "claude",
            "parser_revision": 1,
            "schema_version": 1,
            "snapshot_at": "2024-01-01T00:00:00Z",
        },
        {
            "session_key": "s2",
            "source": "claude",
            "parser_revision": 1,
            "schema_version": 1,
            "snapshot_at": "2024-01-01T00:00:00Z",
        },
    ]
    result = await engine.upload_metadata_batch(sessions)
    assert result["ingested"] == 2
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_upload_engine_canonical() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_client.put.return_value = mock_response

    engine = UploadEngine(client=mock_client, api_url="https://api.example.com")

    data = {"messages": [{"role": "user", "content": "hello"}]}
    result = await engine.upload_canonical("session-key-1", data)
    assert result["status"] == "ok"

    # Verify gzip content was sent
    call_kwargs = mock_client.put.call_args
    assert call_kwargs[1]["headers"]["Content-Encoding"] == "gzip"


@pytest.mark.asyncio
async def test_upload_engine_raw() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_client.put.return_value = mock_response

    engine = UploadEngine(client=mock_client, api_url="https://api.example.com")

    raw_data = {"raw": True, "events": [1, 2, 3]}
    result = await engine.upload_raw("session-key-1", raw_data, "abc123hash")
    assert result["status"] == "ok"
