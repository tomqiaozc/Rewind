"""Azure Blob Storage service for managing session content.

Blob layout:
    {user_id}/{session_key}/canonical.json.gz        # overwritten on re-ingest
    {user_id}/{session_key}/raw/{raw_hash}.json.gz   # immutable, content-addressed
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient, ContainerClient

from src.config import settings

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Async Azure Blob Storage operations for session content."""

    def __init__(self, connection_string: str, container_name: str) -> None:
        self._connection_string = connection_string
        self._container_name = container_name
        # Lazy-initialised; created on first I/O call so construction never
        # fails when Azure transport (aiohttp) is unavailable (e.g. in tests).
        self._blob_service_client: BlobServiceClient | None = None

    # ------------------------------------------------------------------
    # Key construction helpers
    # ------------------------------------------------------------------

    def _canonical_key(self, user_id: str, session_key: str) -> str:
        """Build the blob key for canonical (processed) content."""
        return f"{user_id}/{session_key}/canonical.json.gz"

    def _raw_key(self, user_id: str, session_key: str, raw_hash: str) -> str:
        """Build the blob key for raw (immutable) content."""
        return f"{user_id}/{session_key}/raw/{raw_hash}.json.gz"

    # ------------------------------------------------------------------
    # Container client helper
    # ------------------------------------------------------------------

    def _get_blob_service_client(self) -> BlobServiceClient:
        """Return the blob service client, creating it lazily on first use."""
        if self._blob_service_client is None:
            self._blob_service_client = BlobServiceClient.from_connection_string(
                self._connection_string
            )
        return self._blob_service_client

    def _get_container_client(self) -> ContainerClient:
        """Return an async container client."""
        return self._get_blob_service_client().get_container_client(self._container_name)

    # ------------------------------------------------------------------
    # Public async operations
    # ------------------------------------------------------------------

    async def upload_canonical(self, user_id: str, session_key: str, data: bytes) -> str:
        """Upload canonical content. Returns blob key. Overwrites existing."""
        key = self._canonical_key(user_id, session_key)
        container = self._get_container_client()
        await container.upload_blob(name=key, data=data, overwrite=True)
        logger.info("Uploaded canonical blob: %s (%d bytes)", key, len(data))
        return key

    async def upload_raw(self, user_id: str, session_key: str, raw_hash: str, data: bytes) -> str:
        """Upload raw content. Returns blob key. Content-addressed, never overwritten."""
        key = self._raw_key(user_id, session_key, raw_hash)
        container = self._get_container_client()
        # overwrite=False ensures content-addressed immutability
        try:
            await container.upload_blob(name=key, data=data, overwrite=False)
            logger.info("Uploaded raw blob: %s (%d bytes)", key, len(data))
        except Exception:
            # If the blob already exists, that's fine — it's content-addressed
            if await self.exists(key):
                logger.debug("Raw blob already exists (content-addressed): %s", key)
            else:
                raise
        return key

    async def download(self, key: str) -> bytes:
        """Download blob by key."""
        container = self._get_container_client()
        blob_client = container.get_blob_client(key)
        stream = await blob_client.download_blob()
        data = await stream.readall()
        logger.debug("Downloaded blob: %s (%d bytes)", key, len(data))
        return data

    async def exists(self, key: str) -> bool:
        """Check if blob exists."""
        container = self._get_container_client()
        blob_client = container.get_blob_client(key)
        try:
            await blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    async def generate_sas_url(self, key: str, expiry_minutes: int = 15) -> str:
        """Generate a SAS URL for direct access to a blob."""
        # Parse account name and key from connection string
        parts = dict(
            part.split("=", 1) for part in self._connection_string.split(";") if "=" in part
        )
        account_name = parts.get("AccountName", "")
        account_key = parts.get("AccountKey", "")

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self._container_name,
            blob_name=key,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )

        # Build the URL from the blob endpoint or default
        blob_endpoint = parts.get("BlobEndpoint", f"https://{account_name}.blob.core.windows.net")
        return f"{blob_endpoint}/{self._container_name}/{key}?{sas_token}"

    async def get_blob_size(self, key: str) -> int:
        """Get size of a blob in bytes."""
        container = self._get_container_client()
        blob_client = container.get_blob_client(key)
        props = await blob_client.get_blob_properties()
        return props.size


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_storage_service() -> BlobStorageService:
    """FastAPI dependency that returns a singleton BlobStorageService."""
    return BlobStorageService(
        connection_string=settings.azure_storage_connection_string,
        container_name=settings.azure_storage_container_name,
    )
