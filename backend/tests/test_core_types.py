from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.core.types import CanonicalMessage, CanonicalSession, RawSessionArchive


class TestCanonicalMessage:
    """Tests for the CanonicalMessage model."""

    def test_minimal_message(self) -> None:
        msg = CanonicalMessage(role="user", ordinal=0, content="Hello")
        assert msg.role == "user"
        assert msg.ordinal == 0
        assert msg.content == "Hello"
        assert msg.tool_name is None
        assert msg.tool_call_id is None
        assert msg.tool_status is None
        assert msg.input_tokens is None
        assert msg.output_tokens is None
        assert msg.started_at is None
        assert msg.ended_at is None

    def test_full_message(self) -> None:
        now = datetime.now(tz=timezone.utc)
        msg = CanonicalMessage(
            role="assistant",
            ordinal=1,
            content="Response text",
            tool_name="bash",
            tool_call_id="tc_123",
            tool_status="success",
            input_tokens=100,
            output_tokens=200,
            started_at=now,
            ended_at=now,
        )
        assert msg.role == "assistant"
        assert msg.ordinal == 1
        assert msg.content == "Response text"
        assert msg.tool_name == "bash"
        assert msg.tool_call_id == "tc_123"
        assert msg.tool_status == "success"
        assert msg.input_tokens == 100
        assert msg.output_tokens == 200
        assert msg.started_at == now
        assert msg.ended_at == now

    def test_tool_role(self) -> None:
        msg = CanonicalMessage(
            role="tool",
            ordinal=2,
            content="tool output",
            tool_name="read_file",
            tool_call_id="tc_456",
            tool_status="success",
        )
        assert msg.role == "tool"
        assert msg.tool_name == "read_file"

    def test_system_role(self) -> None:
        msg = CanonicalMessage(role="system", ordinal=0, content="System prompt")
        assert msg.role == "system"

    def test_invalid_role_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalMessage(role="invalid", ordinal=0, content="test")

    def test_negative_ordinal_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalMessage(role="user", ordinal=-1, content="test")

    def test_serialization_roundtrip(self) -> None:
        now = datetime.now(tz=timezone.utc)
        msg = CanonicalMessage(role="assistant", ordinal=5, content="Hello", started_at=now)
        data = msg.model_dump()
        restored = CanonicalMessage.model_validate(data)
        assert restored == msg


class TestCanonicalSession:
    """Tests for the CanonicalSession model."""

    def test_minimal_session(self) -> None:
        now = datetime.now(tz=timezone.utc)
        session = CanonicalSession(
            session_key="abc-123",
            source="claude",
            started_at=now,
            snapshot_at=now,
            user_messages=1,
            assistant_messages=1,
            total_messages=2,
            content_hash="sha256:abc",
            raw_hash="sha256:def",
            parser_revision=1,
            schema_version=1,
            messages=[
                CanonicalMessage(role="user", ordinal=0, content="Hi"),
                CanonicalMessage(role="assistant", ordinal=1, content="Hello"),
            ],
        )
        assert session.session_key == "abc-123"
        assert session.source == "claude"
        assert session.total_messages == 2
        assert len(session.messages) == 2
        # Optional fields default to None
        assert session.last_message_at is None
        assert session.duration_seconds is None
        assert session.total_input_tokens is None
        assert session.total_output_tokens is None
        assert session.total_cached_tokens is None
        assert session.project_ref is None
        assert session.project_name is None
        assert session.model is None
        assert session.title is None
        assert session.summary is None

    def test_full_session(self) -> None:
        now = datetime.now(tz=timezone.utc)
        session = CanonicalSession(
            session_key="session-001",
            source="opencode",
            started_at=now,
            last_message_at=now,
            duration_seconds=120,
            snapshot_at=now,
            user_messages=5,
            assistant_messages=5,
            total_messages=10,
            total_input_tokens=1000,
            total_output_tokens=2000,
            total_cached_tokens=500,
            project_ref="/home/user/project",
            project_name="my-project",
            model="claude-sonnet-4-20250514",
            title="Refactoring session",
            summary="Refactored the core module",
            content_hash="sha256:abc123",
            raw_hash="sha256:def456",
            parser_revision=1,
            schema_version=1,
            messages=[],
        )
        assert session.source == "opencode"
        assert session.duration_seconds == 120
        assert session.total_input_tokens == 1000
        assert session.model == "claude-sonnet-4-20250514"

    def test_all_source_types(self) -> None:
        now = datetime.now(tz=timezone.utc)
        for source in ("claude", "opencode", "gemini", "codex", "copilot"):
            session = CanonicalSession(
                session_key=f"key-{source}",
                source=source,
                started_at=now,
                snapshot_at=now,
                user_messages=0,
                assistant_messages=0,
                total_messages=0,
                content_hash="sha256:x",
                raw_hash="sha256:y",
                parser_revision=1,
                schema_version=1,
                messages=[],
            )
            assert session.source == source

    def test_invalid_source_rejected(self) -> None:
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(ValidationError):
            CanonicalSession(
                session_key="key",
                source="vscode",
                started_at=now,
                snapshot_at=now,
                user_messages=0,
                assistant_messages=0,
                total_messages=0,
                content_hash="sha256:x",
                raw_hash="sha256:y",
                parser_revision=1,
                schema_version=1,
                messages=[],
            )

    def test_serialization_roundtrip(self) -> None:
        now = datetime.now(tz=timezone.utc)
        session = CanonicalSession(
            session_key="key-rt",
            source="gemini",
            started_at=now,
            snapshot_at=now,
            user_messages=1,
            assistant_messages=0,
            total_messages=1,
            content_hash="sha256:rt",
            raw_hash="sha256:rt2",
            parser_revision=1,
            schema_version=1,
            messages=[CanonicalMessage(role="user", ordinal=0, content="test")],
        )
        data = session.model_dump()
        restored = CanonicalSession.model_validate(data)
        assert restored == session


class TestRawSessionArchive:
    """Tests for the RawSessionArchive model."""

    def test_raw_session_archive(self) -> None:
        now = datetime.now(tz=timezone.utc)
        archive = RawSessionArchive(
            session_key="raw-001",
            source="copilot",
            raw_data={"some": "data", "nested": [1, 2, 3]},
            snapshot_at=now,
        )
        assert archive.session_key == "raw-001"
        assert archive.source == "copilot"
        assert archive.raw_data == {"some": "data", "nested": [1, 2, 3]}
        assert archive.snapshot_at == now

    def test_raw_data_accepts_any_type(self) -> None:
        now = datetime.now(tz=timezone.utc)
        # raw_data can be a list, string, dict, etc.
        for raw in ({"key": "val"}, [1, 2], "string_data", 42):
            archive = RawSessionArchive(
                session_key="raw-any",
                source="claude",
                raw_data=raw,
                snapshot_at=now,
            )
            assert archive.raw_data == raw
