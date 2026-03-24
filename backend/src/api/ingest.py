"""Ingest API routes — CLI session data ingestion endpoints."""
from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.auth.dependencies import get_current_user
from src.config import settings
from src.db.session import get_db
from src.schemas.ingest import (
    BatchIngestRequest,
    BatchIngestResponse,
    PresignRequest,
    PresignResponse,
    RawConfirmRequest,
)
from src.services.ingest import (
    confirm_raw_upload,
    generate_presign_url,
    process_canonical_upload,
    process_raw_proxy_upload,
    upsert_session_batch,
)
from src.services.storage import get_storage_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.models.base import User
    from src.services.storage import BlobStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/sessions", response_model=BatchIngestResponse)
async def batch_metadata_upsert(
    request: Request,
    body: BatchIngestRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BatchIngestResponse:
    """Batch metadata upsert for sessions.

    Accepts up to 50 session snapshots. Body must not exceed 2MB.
    """
    # Check metadata size limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_metadata_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body exceeds {settings.max_metadata_size_bytes} byte limit",
        )

    # Check batch size
    if len(body.sessions) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch size exceeds {settings.max_batch_size} sessions",
        )

    ingested, skipped = await upsert_session_batch(db, user.id, body.sessions)
    return BatchIngestResponse(ingested=ingested, skipped=skipped)


@router.put("/content/{session_key}/canonical")
async def upload_canonical(
    session_key: str,
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    storage: BlobStorageService = Depends(get_storage_service),  # noqa: B008
) -> dict[str, object]:
    """Upload canonical (processed) content for a session.

    Accepts gzip-compressed JSON. Requires Content-Length header.
    """
    # Require Content-Length
    content_length_header = request.headers.get("content-length")
    if not content_length_header:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Content-Length header is required",
        )

    content_length = int(content_length_header)

    # Check compressed size
    if content_length > settings.max_content_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content exceeds {settings.max_content_size_bytes} byte limit",
        )

    # Read body
    compressed_data = await request.body()

    try:
        result = await process_canonical_upload(
            db, storage, user.id, session_key, compressed_data
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_key}' not found. Ingest metadata first.",
        ) from exc
    except ValueError as exc:
        # Decompression size limit exceeded (gzip bomb)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    return result


@router.put("/content/{session_key}/raw")
async def upload_raw_proxy(
    session_key: str,
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    storage: BlobStorageService = Depends(get_storage_service),  # noqa: B008
) -> dict[str, object]:
    """Proxy raw upload — fallback when direct upload fails.

    Accepts gzip-compressed JSON. Requires Content-Length header.
    """
    # Require Content-Length
    content_length_header = request.headers.get("content-length")
    if not content_length_header:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Content-Length header is required",
        )

    content_length = int(content_length_header)

    if content_length > settings.max_content_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content exceeds {settings.max_content_size_bytes} byte limit",
        )

    # Read body
    compressed_data = await request.body()

    # Extract raw_hash from query param or compute from body
    raw_hash = request.query_params.get("raw_hash")
    if not raw_hash:
        raw_hash = hashlib.sha256(compressed_data).hexdigest()

    try:
        result = await process_raw_proxy_upload(
            db, storage, user.id, session_key, compressed_data, raw_hash
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_key}' not found. Ingest metadata first.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    return result


@router.post("/content/{session_key}/raw/confirm")
async def confirm_raw(
    session_key: str,
    body: RawConfirmRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    storage: BlobStorageService = Depends(get_storage_service),  # noqa: B008
) -> dict[str, object]:
    """Confirm raw upload after direct upload to blob storage."""
    try:
        result = await confirm_raw_upload(
            db, storage, user.id, session_key, body.raw_hash, body.raw_size
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return result


@router.post("/presign", response_model=PresignResponse)
async def presign(
    body: PresignRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    storage: BlobStorageService = Depends(get_storage_service),  # noqa: B008
) -> PresignResponse:
    """Generate a pre-signed SAS URL for direct raw upload."""
    upload_url, blob_key = await generate_presign_url(
        storage, user.id, body.session_key, body.raw_hash
    )
    return PresignResponse(upload_url=upload_url, blob_key=blob_key)
