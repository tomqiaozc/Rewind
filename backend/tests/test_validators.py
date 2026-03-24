from __future__ import annotations

import pytest

from src.core.validators import build_title, validate_session_key, validate_source


class TestValidateSource:
    """Tests for validate_source."""

    def test_valid_sources(self) -> None:
        for source in ("claude", "opencode", "gemini", "codex", "copilot"):
            assert validate_source(source) == source

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            validate_source("vscode")

    def test_empty_source_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            validate_source("")

    def test_case_sensitive(self) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            validate_source("Claude")


class TestValidateSessionKey:
    """Tests for validate_session_key."""

    def test_valid_key(self) -> None:
        assert validate_session_key("abc-123") == "abc-123"

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Session key"):
            validate_session_key("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="Session key"):
            validate_session_key("   ")

    def test_strips_whitespace(self) -> None:
        assert validate_session_key("  key-001  ") == "key-001"


class TestBuildTitle:
    """Tests for build_title."""

    def test_with_project_and_message(self) -> None:
        title = build_title("/home/user/my-project", "Fix the login bug")
        assert title == "[my-project] Fix the login bug"

    def test_none_when_both_none(self) -> None:
        assert build_title(None, None) is None

    def test_none_when_both_empty(self) -> None:
        assert build_title("", "") is None

    def test_project_only(self) -> None:
        title = build_title("/home/user/project", None)
        assert title == "[project]"

    def test_message_only(self) -> None:
        title = build_title(None, "Hello world")
        assert title == "Hello world"

    def test_truncation_on_word_boundary(self) -> None:
        long_message = "word " * 30  # 150 chars
        title = build_title(None, long_message)
        assert title is not None
        assert len(title) <= 80
        assert title.endswith("...")

    def test_truncation_with_project_prefix(self) -> None:
        long_message = "a " * 50
        title = build_title("/path/to/project", long_message)
        assert title is not None
        assert len(title) <= 80
        assert title.startswith("[project]")
        assert title.endswith("...")

    def test_whitespace_normalization(self) -> None:
        title = build_title("/path/to/proj", "  hello   world  ")
        assert title == "[proj] hello world"

    def test_newline_normalization(self) -> None:
        title = build_title(None, "line one\nline two\ttab")
        assert title == "line one line two tab"

    def test_exact_max_length_no_truncation(self) -> None:
        msg = "a" * 80
        title = build_title(None, msg)
        assert title is not None
        assert len(title) == 80
        assert not title.endswith("...")

    def test_last_path_segment_used(self) -> None:
        title = build_title("/a/b/c/deep-project", "test")
        assert title == "[deep-project] test"

    def test_trailing_slash_handled(self) -> None:
        title = build_title("/a/b/project/", "test")
        assert title == "[project] test"
