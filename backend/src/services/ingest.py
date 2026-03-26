"""Ingest service — business logic for session metadata upsert and content uploads."""

from __future__ import annotations

import gzip
import hashlib
import io
import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, or_, select
from sqlalchemy import func as sa_func
from sqlalchemy.dialects.postgresql import insert

from src.core.chunking import chunk_message
from src.core.constants import MAX_DECOMPRESSED_SIZE_BYTES
from src.models.session import Message, MessageChunk, Session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.schemas.ingest import SessionSnapshot
    from src.services.storage import BlobStorageService

logger = logging.getLogger(__name__)


async def upsert_session_batch(
    db: AsyncSession,
    user_id: uuid.UUID,
    snapshots: list[SessionSnapshot],
) -> tuple[int, int]:
    """Upsert a batch of session metadata snapshots.

    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE ... WHERE to implement
    the 4-field idempotency check.

    Returns (ingested_count, skipped_count).
    """
    ingested = 0

    for snapshot in snapshots:
        session_id = uuid.uuid4()

        stmt = insert(Session).values(
            id=session_id,
            user_id=user_id,
            session_key=snapshot.session_key,
            source=snapshot.source,
            started_at=snapshot.started_at,
            last_message_at=snapshot.last_message_at,
            duration_seconds=snapshot.duration_seconds,
            snapshot_at=snapshot.snapshot_at,
            user_messages=snapshot.user_messages,
            assistant_messages=snapshot.assistant_messages,
            total_messages=snapshot.total_messages,
            total_input_tokens=snapshot.total_input_tokens,
            total_output_tokens=snapshot.total_output_tokens,
            total_cached_tokens=snapshot.total_cached_tokens,
            project_ref=snapshot.project_ref,
            project_name=snapshot.project_name,
            model=snapshot.model,
            title=snapshot.title,
            summary=snapshot.summary,
            content_hash=snapshot.content_hash,
            raw_hash=snapshot.raw_hash,
            parser_revision=snapshot.parser_revision,
            schema_version=snapshot.schema_version,
            ingested_at=sa_func.now(),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "session_key"],
            set_={
                "source": stmt.excluded.source,
                "started_at": stmt.excluded.started_at,
                "last_message_at": stmt.excluded.last_message_at,
                "duration_seconds": stmt.excluded.duration_seconds,
                "snapshot_at": stmt.excluded.snapshot_at,
                "user_messages": stmt.excluded.user_messages,
                "assistant_messages": stmt.excluded.assistant_messages,
                "total_messages": stmt.excluded.total_messages,
                "total_input_tokens": stmt.excluded.total_input_tokens,
                "total_output_tokens": stmt.excluded.total_output_tokens,
                "total_cached_tokens": stmt.excluded.total_cached_tokens,
                "project_ref": stmt.excluded.project_ref,
                "project_name": stmt.excluded.project_name,
                "model": stmt.excluded.model,
                "title": stmt.excluded.title,
                "summary": stmt.excluded.summary,
                "content_hash": stmt.excluded.content_hash,
                "raw_hash": stmt.excluded.raw_hash,
                "parser_revision": stmt.excluded.parser_revision,
                "schema_version": stmt.excluded.schema_version,
                "ingested_at": sa_func.now(),
                "updated_at": sa_func.now(),
            },
            where=and_(
                # Only update if the incoming version is >= the stored version
                stmt.excluded.parser_revision >= Session.parser_revision,
                stmt.excluded.schema_version >= Session.schema_version,
                # And at least one of: content changed or version bumped
                or_(
                    stmt.excluded.content_hash != Session.content_hash,
                    stmt.excluded.raw_hash != Session.raw_hash,
                    stmt.excluded.parser_revision > Session.parser_revision,
                    stmt.excluded.schema_version > Session.schema_version,
                ),
            ),
        )

        result = await db.execute(stmt)
        # PostgreSQL returns rowcount=1 for both INSERT and UPDATE,
        # and rowcount=0 when the WHERE clause prevents the update.
        if result.rowcount > 0:
            ingested += 1

    await db.commit()

    skipped = len(snapshots) - ingested
    return ingested, skipped


def _decompress_with_limit(
    compressed_data: bytes,
    max_decompressed: int = MAX_DECOMPRESSED_SIZE_BYTES,
) -> bytes:
    """Decompress gzip data with a decompressed size limit (gzip bomb defense).

    Raises ValueError if the decompressed data exceeds the limit.
    """
    decompressor = gzip.GzipFile(fileobj=io.BytesIO(compressed_data))
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = decompressor.read(65536)  # 64KB reads
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_decompressed:
            raise ValueError(f"Decompressed data exceeds {max_decompressed} byte limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def process_canonical_upload(
    db: AsyncSession,
    storage: BlobStorageService,
    user_id: uuid.UUID,
    session_key: str,
    compressed_data: bytes,
) -> dict[str, object]:
    """Process a canonical content upload.

    1. Verify session exists for this user
    2. Decompress with size limit
    3. Compute content_hash from decompressed data
    4. Upload compressed data to blob storage
    5. Update session with content_key, content_size, content_hash
    6. Parse messages and create FTS chunks

    Returns dict with content_key, content_size, content_hash.
    """
    import json

    # 1. Verify session exists
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.session_key == session_key,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise LookupError(f"Session '{session_key}' not found for user")

    # 2. Decompress with gzip bomb defense
    decompressed = _decompress_with_limit(compressed_data)

    # 3. Compute content hash
    content_hash = hashlib.sha256(decompressed).hexdigest()

    # 4. Upload compressed data to blob
    user_id_str = str(user_id)
    content_key = await storage.upload_canonical(user_id_str, session_key, compressed_data)

    # 5. Update session metadata
    content_size = len(decompressed)
    session.content_key = content_key
    session.content_size = content_size
    session.content_hash = content_hash
    await db.commit()

    # 6. Parse messages from decompressed JSON and create FTS chunks
    try:
        payload = json.loads(decompressed)
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
    except (json.JSONDecodeError, UnicodeDecodeError):
        messages = []

    if messages:
        await process_messages_and_chunks(db, session.id, messages)

    return {
        "content_key": content_key,
        "content_size": content_size,
        "content_hash": content_hash,
    }


async def process_messages_and_chunks(
    db: AsyncSession,
    session_id: uuid.UUID,
    messages: list[dict[str, object]],
) -> int:
    """Delete existing messages/chunks and re-insert with FTS chunking.

    Returns the number of messages inserted.
    """
    # Delete existing chunks first (they reference messages via FK)
    await db.execute(delete(MessageChunk).where(MessageChunk.session_id == session_id))
    # Delete existing messages
    await db.execute(delete(Message).where(Message.session_id == session_id))

    inserted = 0
    for msg_data in messages:
        role = msg_data.get("role", "user")
        ordinal = msg_data.get("ordinal", inserted)
        content = msg_data.get("content", "")

        message_id = uuid.uuid4()
        msg = Message(
            id=message_id,
            session_id=session_id,
            role=str(role),
            ordinal=int(ordinal),  # type: ignore[arg-type]
            tool_name=msg_data.get("tool_name"),  # type: ignore[arg-type]
            tool_call_id=msg_data.get("tool_call_id"),  # type: ignore[arg-type]
            tool_status=msg_data.get("tool_status"),  # type: ignore[arg-type]
            input_tokens=int(msg_data.get("input_tokens", 0) or 0),
            output_tokens=int(msg_data.get("output_tokens", 0) or 0),
        )
        db.add(msg)

        # Create FTS chunks
        text_content = str(content) if content else ""
        if text_content.strip():
            chunks = chunk_message(text_content)
            for idx, chunk_text in enumerate(chunks):
                chunk = MessageChunk(
                    id=uuid.uuid4(),
                    message_id=message_id,
                    session_id=session_id,
                    chunk_index=idx,
                    content=chunk_text,
                    tool_context=msg_data.get("tool_name"),  # type: ignore[arg-type]
                )
                db.add(chunk)

        inserted += 1

    await db.commit()
    return inserted


async def process_raw_proxy_upload(
    db: AsyncSession,
    storage: BlobStorageService,
    user_id: uuid.UUID,
    session_key: str,
    compressed_data: bytes,
    raw_hash: str,
) -> dict[str, object]:
    """Process a raw content upload via proxy (fallback path).

    1. Verify session exists
    2. Decompress with size limit (gzip bomb defense)
    3. Upload to blob storage
    4. Update session with raw_key, raw_size, raw_hash

    Returns dict with raw_key, raw_size, raw_hash.
    """
    # 1. Verify session exists
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.session_key == session_key,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise LookupError(f"Session '{session_key}' not found for user")

    # 2. Decompress with gzip bomb defense (verify size)
    decompressed = _decompress_with_limit(compressed_data)

    # 3. Upload to blob
    user_id_str = str(user_id)
    raw_key = await storage.upload_raw(user_id_str, session_key, raw_hash, compressed_data)

    # 4. Update session
    raw_size = len(decompressed)
    session.raw_key = raw_key
    session.raw_size = raw_size
    session.raw_hash = raw_hash
    await db.commit()

    return {
        "raw_key": raw_key,
        "raw_size": raw_size,
        "raw_hash": raw_hash,
    }


async def confirm_raw_upload(
    db: AsyncSession,
    storage: BlobStorageService,
    user_id: uuid.UUID,
    session_key: str,
    raw_hash: str,
    raw_size: int,
) -> dict[str, object]:
    """Confirm a raw upload after direct upload to blob storage.

    1. Verify session exists
    2. Verify blob exists in storage
    3. Update session with raw_key, raw_size, raw_hash

    Returns dict with raw_key, raw_size, raw_hash.
    """
    # 1. Verify session exists
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.session_key == session_key,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise LookupError(f"Session '{session_key}' not found for user")

    # 2. Compute expected blob key and verify it exists
    user_id_str = str(user_id)
    raw_key = storage._raw_key(user_id_str, session_key, raw_hash)  # noqa: SLF001
    if not await storage.exists(raw_key):
        raise LookupError(f"Raw blob not found at '{raw_key}'")

    # 3. Update session
    session.raw_key = raw_key
    session.raw_size = raw_size
    session.raw_hash = raw_hash
    await db.commit()

    return {
        "raw_key": raw_key,
        "raw_size": raw_size,
        "raw_hash": raw_hash,
    }


async def generate_presign_url(
    storage: BlobStorageService,
    user_id: uuid.UUID,
    session_key: str,
    raw_hash: str,
) -> tuple[str, str]:
    """Generate a SAS URL for direct raw upload.

    Returns (upload_url, blob_key).
    """
    user_id_str = str(user_id)
    blob_key = storage._raw_key(user_id_str, session_key, raw_hash)  # noqa: SLF001
    upload_url = await storage.generate_sas_url(blob_key, expiry_minutes=15)
    return upload_url, blob_key
