"""Tests for Claude Code parser."""
from __future__ import annotations

from pathlib import Path

from src.parsers.claude import ClaudeParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_claude_session() -> None:
    parser = ClaudeParser(base_dir=FIXTURES_DIR)
    # Parse a single file directly
    results = parser.parse_file(FIXTURES_DIR / "claude_session.jsonl", "test-project")
    assert len(results) == 1
    r = results[0]
    assert r.canonical.source == "claude"
    assert r.canonical.total_messages == 4
    assert r.canonical.user_messages == 2
    assert r.canonical.assistant_messages == 2


def test_claude_content_blocks() -> None:
    parser = ClaudeParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "claude_session.jsonl", "test-project")
    r = results[0]
    msgs = r.canonical.messages
    # First assistant message: text block
    assert "I'm doing well" in msgs[1].content
    # Second assistant message: tool_use + text
    assert "Read" in (msgs[3].content or "")  # tool use info should be in content


def test_claude_token_counting() -> None:
    parser = ClaudeParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "claude_session.jsonl", "test-project")
    r = results[0]
    assert r.canonical.total_input_tokens == 30  # 10 + 20
    assert r.canonical.total_output_tokens == 45  # 15 + 30


def test_claude_timestamps() -> None:
    parser = ClaudeParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "claude_session.jsonl", "test-project")
    r = results[0]
    assert r.canonical.started_at is not None
    assert r.canonical.last_message_at is not None
    assert r.canonical.started_at < r.canonical.last_message_at


def test_claude_dual_output() -> None:
    parser = ClaudeParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "claude_session.jsonl", "test-project")
    r = results[0]
    # Must have both canonical and raw
    assert r.canonical is not None
    assert r.raw is not None
    assert r.raw.source == "claude"
    assert len(r.raw.raw_data) > 0  # raw events preserved


def test_claude_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    parser = ClaudeParser(base_dir=tmp_path)
    results = parser.parse_file(f, "test")
    assert len(results) == 0


def test_claude_malformed_line(tmp_path: Path) -> None:
    f = tmp_path / "bad.jsonl"
    f.write_text(
        'not valid json\n'
        '{"type":"human","message":{"role":"user","content":"ok"},'
        '"timestamp":"2024-01-01T00:00:00Z"}\n'
    )
    parser = ClaudeParser(base_dir=tmp_path)
    parser.parse_file(f, "test")
    # Should parse the valid line and log the bad one
    assert len(parser.errors) >= 1
    # The valid line should still produce a result if there are messages
    # (A single user message may or may not produce a session depending on implementation)
