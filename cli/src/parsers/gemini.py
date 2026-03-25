"""Gemini CLI session parser — reads ~/.gemini/tmp/*/chats/session-*.json."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.config.cursors import FileCursor
from src.core.constants import PARSER_REVISION, SCHEMA_VERSION
from src.core.types import (
    CanonicalMessage,
    CanonicalSession,
    RawSessionArchive,
)
from src.parsers.base import BaseParser, ParseResult
from src.upload.content import compute_hash
from src.utils.file_identity import get_file_identity

logger = logging.getLogger(__name__)

_DEFAULT_BASE_DIR = Path.home() / ".gemini" / "tmp"

# Gemini roles that map to canonical message roles
_ROLE_MAP = {
    "user": "user",
    "model": "assistant",
}

# Message types to skip
_SKIP_TYPES = {"info"}


class GeminiParser(BaseParser):
    """Parser for Gemini CLI JSON session files."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or _DEFAULT_BASE_DIR
        super().__init__()

    @property
    def source_name(self) -> str:
        return "gemini"

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[Path]:
        """Find all session-*.json files under base_dir/**/chats/."""
        if not self._base_dir.is_dir():
            return []
        return sorted(self._base_dir.glob("**/chats/session-*.json"))

    # ------------------------------------------------------------------
    # Bulk parse
    # ------------------------------------------------------------------

    def parse_all(self) -> list[ParseResult]:
        """Discover and parse every session JSON file."""
        results: list[ParseResult] = []
        for path in self.discover():
            results.extend(self.parse_file(path))
        return results

    # ------------------------------------------------------------------
    # Single-file parse
    # ------------------------------------------------------------------

    def parse_file(self, path: Path) -> list[ParseResult]:
        """Parse a single Gemini session JSON file into a ParseResult."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.log_error(str(path), f"Cannot read file: {exc}")
            return []

        if not text.strip():
            return []

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            self.log_error(str(path), f"Malformed JSON: {exc}")
            return []

        session_id = data.get("id", path.stem)
        project_ref = data.get("projectHash")
        project_name = data.get("projectName")
        raw_messages = data.get("messages", [])

        messages: list[CanonicalMessage] = []
        timestamps: list[datetime] = []
        model: Optional[str] = None
        total_input_tokens = 0
        total_output_tokens = 0
        ordinal = 0

        for msg in raw_messages:
            msg_type = msg.get("type", "")
            if msg_type in _SKIP_TYPES:
                continue

            raw_role = msg.get("role", "")
            canonical_role = _ROLE_MAP.get(raw_role)
            if canonical_role is None:
                continue

            content = msg.get("content", "")
            ts = self._parse_timestamp(msg.get("createdAt"))
            if ts is not None:
                timestamps.append(ts)

            # Token usage & model from metadata (assistant messages)
            metadata = msg.get("metadata", {}) or {}
            input_tok = metadata.get("inputTokens")
            output_tok = metadata.get("outputTokens")
            if input_tok:
                total_input_tokens += input_tok
            if output_tok:
                total_output_tokens += output_tok

            msg_model = metadata.get("model")
            if msg_model:
                model = msg_model

            cm = CanonicalMessage(
                role=canonical_role,  # type: ignore[arg-type]
                ordinal=ordinal,
                content=content,
                input_tokens=input_tok,
                output_tokens=output_tok,
                started_at=ts,
                ended_at=ts,
            )
            messages.append(cm)
            ordinal += 1

        # No messages → nothing to return
        if not messages:
            return []

        # Session key
        session_key = f"gemini:{session_id}"

        now = datetime.now(timezone.utc)
        started_at = timestamps[0] if timestamps else now
        last_message_at = timestamps[-1] if timestamps else now
        duration = (
            int((last_message_at - started_at).total_seconds())
            if len(timestamps) >= 2
            else None
        )

        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        # Hashes
        canonical_data = [m.model_dump(mode="json") for m in messages]
        content_hash = compute_hash(canonical_data)
        raw_hash = compute_hash(data)

        canonical = CanonicalSession(
            session_key=session_key,
            source="gemini",
            started_at=started_at,
            last_message_at=last_message_at,
            duration_seconds=duration,
            snapshot_at=now,
            user_messages=user_count,
            assistant_messages=assistant_count,
            total_messages=len(messages),
            total_input_tokens=total_input_tokens or None,
            total_output_tokens=total_output_tokens or None,
            project_ref=project_ref,
            project_name=project_name,
            model=model,
            content_hash=content_hash,
            raw_hash=raw_hash,
            parser_revision=PARSER_REVISION,
            schema_version=SCHEMA_VERSION,
            messages=messages,
        )

        raw = RawSessionArchive(
            session_key=session_key,
            source="gemini",
            raw_data=data,
            snapshot_at=now,
        )

        # File cursor
        identity = get_file_identity(path)
        cursor = FileCursor(
            inode=identity.inode,
            mtime=identity.mtime,
            size=identity.size,
            byte_offset=identity.size,
        )

        return [
            ParseResult(
                canonical=canonical,
                raw=raw,
                cursor_key=session_key,
                cursor=cursor,
                errors=[e.message for e in self.errors],
            )
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        """Parse an ISO 8601 timestamp string."""
        if not value:
            return None
        try:
            # Handle trailing Z for Python 3.9 compatibility
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
