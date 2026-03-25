"""OpenCode session parser — reads SQLite DB or JSON fallback files."""
from __future__ import annotations

import json
import logging
import sqlite3
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

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = (
    Path.home() / ".local" / "share" / "opencode" / "opencode.db"
)
_DEFAULT_STORAGE_DIR = (
    Path.home() / ".local" / "share" / "opencode" / "storage"
)


class OpenCodeParser(BaseParser):
    """Parser for OpenCode sessions (SQLite primary, JSON fallback)."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._storage_dir = storage_dir or _DEFAULT_STORAGE_DIR
        super().__init__()

    @property
    def source_name(self) -> str:
        return "opencode"

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[Path]:
        """Return DB path if it exists, else JSON storage files."""
        if self._db_path.is_file():
            return [self._db_path]
        if self._storage_dir.is_dir():
            return sorted(self._storage_dir.rglob("*.json"))
        return []

    # ------------------------------------------------------------------
    # Bulk parse
    # ------------------------------------------------------------------

    def parse_all(self) -> list[ParseResult]:
        """Parse all sessions, trying SQLite first then JSON fallback."""
        results = self._parse_sqlite()
        if results:
            return results
        # Fallback to JSON if SQLite produced nothing
        return self._parse_json_fallback()

    # ------------------------------------------------------------------
    # SQLite parsing
    # ------------------------------------------------------------------

    def _parse_sqlite(self) -> list[ParseResult]:
        """Parse sessions from the OpenCode SQLite database."""
        if not self._db_path.is_file():
            return []

        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:
            self.log_error(
                str(self._db_path), f"Cannot open database: {exc}"
            )
            return []

        results: list[ParseResult] = []
        try:
            sessions = conn.execute(
                "SELECT id, path, title, created_at, updated_at "
                "FROM session"
            ).fetchall()

            for sess in sessions:
                result = self._parse_sqlite_session(conn, dict(sess))
                if result is not None:
                    results.append(result)
        except sqlite3.Error as exc:
            self.log_error(
                str(self._db_path), f"Database query error: {exc}"
            )
        finally:
            conn.close()

        return results

    def _parse_sqlite_session(
        self,
        conn: sqlite3.Connection,
        sess: dict[str, Any],
    ) -> Optional[ParseResult]:
        """Parse a single session from SQLite rows."""
        session_id = sess["id"]

        # Fetch messages ordered by created_at
        msg_rows = conn.execute(
            "SELECT id, role, created_at FROM message "
            "WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()

        if not msg_rows:
            return None

        messages: list[CanonicalMessage] = []
        raw_messages: list[dict[str, Any]] = []
        timestamps: list[datetime] = []
        ordinal = 0

        for msg_row in msg_rows:
            msg = dict(msg_row)
            msg_id = msg["id"]
            role = msg["role"]

            # Fetch parts for this message
            part_rows = conn.execute(
                "SELECT id, type, content, tool_name, "
                "tool_call_id, created_at "
                "FROM part WHERE message_id = ? "
                "ORDER BY created_at",
                (msg_id,),
            ).fetchall()

            parts_data: list[dict[str, Any]] = [
                dict(p) for p in part_rows
            ]
            content = self._assemble_parts(parts_data)
            ts = self._parse_timestamp(msg.get("created_at"))
            if ts is not None:
                timestamps.append(ts)

            if role in ("user", "assistant"):
                cm = CanonicalMessage(
                    role=role,  # type: ignore[arg-type]
                    ordinal=ordinal,
                    content=content,
                    started_at=ts,
                    ended_at=ts,
                )
                messages.append(cm)
                ordinal += 1

            raw_messages.append({**msg, "parts": parts_data})

        if not messages:
            return None

        return self._build_result(
            session_id=session_id,
            title=sess.get("title"),
            project_path=sess.get("path"),
            messages=messages,
            timestamps=timestamps,
            raw_data={"session": sess, "messages": raw_messages},
        )

    # ------------------------------------------------------------------
    # JSON fallback parsing
    # ------------------------------------------------------------------

    def _parse_json_fallback(self) -> list[ParseResult]:
        """Parse sessions from JSON fallback files."""
        if not self._storage_dir.is_dir():
            return []

        session_dir = self._storage_dir / "session"
        message_dir = self._storage_dir / "message"
        part_dir = self._storage_dir / "part"

        if not session_dir.is_dir():
            return []

        # Load all entities
        sessions = self._load_json_dir(session_dir)
        all_messages = (
            self._load_json_dir(message_dir)
            if message_dir.is_dir()
            else []
        )
        all_parts = (
            self._load_json_dir(part_dir)
            if part_dir.is_dir()
            else []
        )

        # Index messages by sessionID and parts by messageID
        msgs_by_session: dict[str, list[dict[str, Any]]] = {}
        for msg in all_messages:
            sid = msg.get("sessionID", "")
            msgs_by_session.setdefault(sid, []).append(msg)

        parts_by_message: dict[str, list[dict[str, Any]]] = {}
        for part in all_parts:
            mid = part.get("messageID", "")
            parts_by_message.setdefault(mid, []).append(part)

        results: list[ParseResult] = []
        for sess in sessions:
            result = self._parse_json_session(
                sess, msgs_by_session, parts_by_message
            )
            if result is not None:
                results.append(result)

        return results

    def _parse_json_session(
        self,
        sess: dict[str, Any],
        msgs_by_session: dict[str, list[dict[str, Any]]],
        parts_by_message: dict[str, list[dict[str, Any]]],
    ) -> Optional[ParseResult]:
        """Parse a single session from JSON data."""
        session_id = sess.get("id", "")
        raw_msgs = msgs_by_session.get(session_id, [])

        # Sort messages by createdAt
        raw_msgs.sort(key=lambda m: m.get("createdAt", ""))

        if not raw_msgs:
            return None

        messages: list[CanonicalMessage] = []
        raw_messages: list[dict[str, Any]] = []
        timestamps: list[datetime] = []
        ordinal = 0

        for msg in raw_msgs:
            msg_id = msg.get("id", "")
            role = msg.get("role", "")

            # Get parts for this message
            msg_parts = parts_by_message.get(msg_id, [])
            msg_parts.sort(key=lambda p: p.get("createdAt", ""))

            # Convert camelCase keys to snake_case for _assemble_parts
            converted_parts: list[dict[str, Any]] = []
            for p in msg_parts:
                converted_parts.append({
                    "type": p.get("type"),
                    "content": p.get("content"),
                    "tool_name": p.get("toolName"),
                    "tool_call_id": p.get("toolCallID"),
                })

            content = self._assemble_parts(converted_parts)
            ts = self._parse_timestamp(msg.get("createdAt"))
            if ts is not None:
                timestamps.append(ts)

            if role in ("user", "assistant"):
                cm = CanonicalMessage(
                    role=role,  # type: ignore[arg-type]
                    ordinal=ordinal,
                    content=content,
                    started_at=ts,
                    ended_at=ts,
                )
                messages.append(cm)
                ordinal += 1

            raw_messages.append({**msg, "parts": msg_parts})

        if not messages:
            return None

        return self._build_result(
            session_id=session_id,
            title=sess.get("title"),
            project_path=sess.get("path"),
            messages=messages,
            timestamps=timestamps,
            raw_data={"session": sess, "messages": raw_messages},
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_result(
        self,
        session_id: str,
        title: Optional[str],
        project_path: Optional[str],
        messages: list[CanonicalMessage],
        timestamps: list[datetime],
        raw_data: Any,
    ) -> ParseResult:
        """Build a ParseResult with canonical + raw output."""
        session_key = f"opencode:{session_id}"
        now = datetime.now(timezone.utc)
        started_at = timestamps[0] if timestamps else now
        last_message_at = timestamps[-1] if timestamps else now
        duration = (
            int((last_message_at - started_at).total_seconds())
            if len(timestamps) >= 2
            else None
        )

        user_count = sum(
            1 for m in messages if m.role == "user"
        )
        assistant_count = sum(
            1 for m in messages if m.role == "assistant"
        )

        # Hashes
        canonical_data = [
            m.model_dump(mode="json") for m in messages
        ]
        content_hash = compute_hash(canonical_data)
        raw_hash = compute_hash(raw_data)

        canonical = CanonicalSession(
            session_key=session_key,
            source="opencode",
            started_at=started_at,
            last_message_at=last_message_at,
            duration_seconds=duration,
            snapshot_at=now,
            user_messages=user_count,
            assistant_messages=assistant_count,
            total_messages=len(messages),
            project_ref=project_path,
            title=title,
            content_hash=content_hash,
            raw_hash=raw_hash,
            parser_revision=PARSER_REVISION,
            schema_version=SCHEMA_VERSION,
            messages=messages,
        )

        raw = RawSessionArchive(
            session_key=session_key,
            source="opencode",
            raw_data=raw_data,
            snapshot_at=now,
        )

        # Cursor — use watermark-based cursor for DB source
        cursor = FileCursor(
            inode=0,
            mtime=0.0,
            size=0,
            watermark=(
                last_message_at.isoformat()
                if last_message_at
                else None
            ),
        )

        return ParseResult(
            canonical=canonical,
            raw=raw,
            cursor_key=session_key,
            cursor=cursor,
            errors=[e.message for e in self.errors],
        )

    @staticmethod
    def _assemble_parts(parts: list[dict[str, Any]]) -> str:
        """Assemble message content from part rows."""
        text_parts: list[str] = []
        for part in parts:
            part_type = part.get("type", "text")
            if part_type == "text":
                content = part.get("content", "")
                if content:
                    text_parts.append(content)
            elif part_type == "tool_use":
                tool_name = part.get("tool_name", "unknown")
                text_parts.append(f"[Tool: {tool_name}]")
            elif part_type == "tool_result":
                text_parts.append("[Tool result]")
            else:
                content = part.get("content", "")
                if content:
                    text_parts.append(content)
        return "\n".join(text_parts) if text_parts else ""

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

    @staticmethod
    def _load_json_dir(dir_path: Path) -> list[dict[str, Any]]:
        """Load all JSON files from a directory."""
        items: list[dict[str, Any]] = []
        for json_file in sorted(dir_path.glob("*.json")):
            try:
                data = json.loads(
                    json_file.read_text(encoding="utf-8")
                )
                if isinstance(data, dict):
                    items.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Skipping %s: %s", json_file, exc
                )
        return items
