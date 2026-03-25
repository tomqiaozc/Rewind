"""Claude Code session parser — reads ~/.claude/projects/**/*.jsonl."""
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

_DEFAULT_BASE_DIR = Path.home() / ".claude" / "projects"


class ClaudeParser(BaseParser):
    """Parser for Claude Code JSONL session files."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or _DEFAULT_BASE_DIR
        super().__init__()

    @property
    def source_name(self) -> str:
        return "claude"

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[Path]:
        """Find all *.jsonl files under base_dir."""
        if not self._base_dir.is_dir():
            return []
        return sorted(self._base_dir.rglob("*.jsonl"))

    # ------------------------------------------------------------------
    # Bulk parse
    # ------------------------------------------------------------------

    def parse_all(self) -> list[ParseResult]:
        """Discover and parse every JSONL file."""
        results: list[ParseResult] = []
        for path in self.discover():
            # Derive project_ref from directory structure.
            # e.g. ~/.claude/projects/<project_ref>/file.jsonl
            try:
                rel = path.relative_to(self._base_dir)
                project_ref = str(rel.parent) if rel.parent != Path(".") else rel.stem
            except ValueError:
                project_ref = path.stem
            results.extend(self.parse_file(path, project_ref))
        return results

    # ------------------------------------------------------------------
    # Single-file parse
    # ------------------------------------------------------------------

    def parse_file(self, path: Path, project_ref: str) -> list[ParseResult]:
        """Parse a single JSONL session file into a ParseResult."""
        raw_events: list[dict[str, Any]] = []
        messages: list[CanonicalMessage] = []
        title: Optional[str] = None
        summary_text: Optional[str] = None
        model: Optional[str] = None
        total_input_tokens = 0
        total_output_tokens = 0
        timestamps: list[datetime] = []
        ordinal = 0

        # Read lines ---------------------------------------------------
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.log_error(str(path), f"Cannot read file: {exc}")
            return []

        if not text.strip():
            return []

        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                self.log_error(str(path), f"Malformed JSON on line {line_no}: {exc}")
                continue

            raw_events.append(event)
            event_type = event.get("type")

            # -- summary event -----------------------------------------
            if event_type == "summary":
                title = event.get("leafTitle") or event.get("title")
                summary_text = event.get("summary")
                model = model or event.get("model")
                continue

            # -- human / assistant messages -----------------------------
            msg_data = event.get("message", {})
            role = msg_data.get("role")
            if role not in ("user", "assistant"):
                continue

            content = self._extract_content(msg_data.get("content", ""))
            ts = self._parse_timestamp(event.get("timestamp"))
            if ts is not None:
                timestamps.append(ts)

            # Token usage (assistant only)
            usage = msg_data.get("usage", {})
            input_tok = usage.get("input_tokens")
            output_tok = usage.get("output_tokens")
            if input_tok:
                total_input_tokens += input_tok
            if output_tok:
                total_output_tokens += output_tok

            # Model
            if role == "assistant" and msg_data.get("model"):
                model = msg_data["model"]

            # Build CanonicalMessage
            cm = CanonicalMessage(
                role=role,  # type: ignore[arg-type]
                ordinal=ordinal,
                content=content,
                input_tokens=input_tok,
                output_tokens=output_tok,
                started_at=ts,
                ended_at=ts,
            )
            messages.append(cm)
            ordinal += 1

        # If no messages parsed, nothing to return ----------------------
        if not messages:
            return []

        # Build session key ---------------------------------------------
        try:
            rel = path.relative_to(self._base_dir)
        except ValueError:
            rel = Path(path.name)
        session_key = f"claude:{rel}"

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

        # Hashes -------------------------------------------------------
        canonical_data = [m.model_dump(mode="json") for m in messages]
        content_hash = compute_hash(canonical_data)
        raw_hash = compute_hash(raw_events)

        canonical = CanonicalSession(
            session_key=session_key,
            source="claude",
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
            model=model,
            title=title,
            summary=summary_text,
            content_hash=content_hash,
            raw_hash=raw_hash,
            parser_revision=PARSER_REVISION,
            schema_version=SCHEMA_VERSION,
            messages=messages,
        )

        raw = RawSessionArchive(
            session_key=session_key,
            source="claude",
            raw_data=raw_events,
            snapshot_at=now,
        )

        # File cursor ---------------------------------------------------
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
    def _extract_content(content: Any) -> str:
        """Extract text from string or content-block array."""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    parts.append(str(block))
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    parts.append(block.get("text", ""))
                elif block_type == "tool_use":
                    name = block.get("name", "unknown")
                    parts.append(f"[Tool: {name}]")
                elif block_type == "tool_result":
                    # Summarize tool results to keep canonical content concise
                    parts.append("[Tool result]")
                else:
                    parts.append(str(block))
            return "\n".join(parts)

        return str(content)

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
