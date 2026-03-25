"""Tests for Gemini CLI parser."""
from __future__ import annotations

import json
from pathlib import Path

from src.parsers.gemini import GeminiParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_gemini_session() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    assert len(results) == 1
    r = results[0]
    assert r.canonical.source == "gemini"
    # 4 real messages (info message skipped)
    assert r.canonical.total_messages == 4
    assert r.canonical.user_messages == 2
    assert r.canonical.assistant_messages == 2


def test_gemini_skips_info_messages() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    msgs = results[0].canonical.messages
    for msg in msgs:
        assert "System info" not in msg.content


def test_gemini_token_counting() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    r = results[0]
    assert r.canonical.total_input_tokens == 40  # 15 + 25
    assert r.canonical.total_output_tokens == 55  # 20 + 35


def test_gemini_project_ref() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    r = results[0]
    assert r.canonical.project_ref == "hash_xyz"
    assert r.canonical.project_name == "/home/user/myproject"


def test_gemini_dual_output() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    r = results[0]
    assert r.canonical is not None
    assert r.raw is not None
    assert r.raw.source == "gemini"


def test_gemini_model_extraction() -> None:
    parser = GeminiParser(base_dir=FIXTURES_DIR)
    results = parser.parse_file(FIXTURES_DIR / "gemini_session.json")
    r = results[0]
    assert r.canonical.model == "gemini-2.0-flash"


def test_gemini_empty_messages(tmp_path: Path) -> None:
    data = {"id": "empty-sess", "messages": []}
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data))
    parser = GeminiParser(base_dir=tmp_path)
    results = parser.parse_file(f)
    assert len(results) == 0  # no messages = no session
