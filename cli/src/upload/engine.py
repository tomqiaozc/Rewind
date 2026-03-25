"""Upload engine — batch metadata POST, content PUT with retry."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from src.upload.content import compress_json

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 50
MAX_RETRIES = 3


class UploadEngine:
    """Handles uploading session data to the Rewind API."""

    def __init__(self, client: httpx.AsyncClient, api_url: str) -> None:
        self._client = client
        self._api_url = api_url.rstrip("/")

    async def upload_metadata_batch(
        self, sessions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """POST batch metadata (up to 50 sessions)."""
        if len(sessions) > MAX_BATCH_SIZE:
            msg = f"Batch size {len(sessions)} exceeds limit {MAX_BATCH_SIZE}"
            raise ValueError(msg)

        url = f"{self._api_url}/api/ingest/sessions"
        response = await self._client.post(
            url,
            json={"sessions": sessions},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def upload_canonical(
        self, session_key: str, canonical_data: Any
    ) -> dict[str, Any]:
        """PUT gzip-compressed canonical content."""
        compressed = compress_json(canonical_data)
        url = f"{self._api_url}/api/ingest/content/{session_key}/canonical"
        response = await self._client.put(
            url,
            content=compressed,
            headers={
                "Content-Type": "application/gzip",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    async def upload_raw(
        self,
        session_key: str,
        raw_data: Any,
        raw_hash: str,
    ) -> dict[str, Any]:
        """PUT gzip-compressed raw content."""
        compressed = compress_json(raw_data)
        url = f"{self._api_url}/api/ingest/content/{session_key}/raw"
        response = await self._client.put(
            url,
            content=compressed,
            headers={
                "Content-Type": "application/gzip",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            params={"raw_hash": raw_hash},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    async def upload_session(
        self,
        metadata: dict[str, Any],
        canonical_data: Any,
        raw_data: Any,
        raw_hash: str,
    ) -> bool:
        """Upload a complete session: metadata + canonical + raw.

        Returns True on success, False on failure.
        """
        try:
            await self.upload_metadata_batch([metadata])
            await self.upload_canonical(metadata["session_key"], canonical_data)
            await self.upload_raw(metadata["session_key"], raw_data, raw_hash)
            return True
        except httpx.HTTPError as exc:
            logger.error("Upload failed for %s: %s", metadata["session_key"], exc)
            return False
