"""Tests for OpenCode parser."""
from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from src.parsers.opencode import OpenCodeParser

if TYPE_CHECKING:
    from pathlib import Path


def _create_test_db(db_path: Path) -> None:
    """Create a minimal OpenCode SQLite database."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE session (
            id TEXT PRIMARY KEY,
            path TEXT,
            title TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE message (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES session(id)
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            type TEXT,
            content TEXT,
            tool_name TEXT,
            tool_call_id TEXT,
            created_at TEXT,
            FOREIGN KEY (message_id) REFERENCES message(id)
        );

        INSERT INTO session VALUES (
            'sess-1', '/home/user/project', 'Test Session',
            '2024-06-01T10:00:00Z', '2024-06-01T10:05:00Z'
        );
        INSERT INTO message VALUES (
            'msg-1', 'sess-1', 'user', '2024-06-01T10:00:00Z'
        );
        INSERT INTO message VALUES (
            'msg-2', 'sess-1', 'assistant', '2024-06-01T10:00:05Z'
        );
        INSERT INTO part VALUES (
            'p-1', 'msg-1', 'text',
            'Hello, can you help me?',
            NULL, NULL, '2024-06-01T10:00:00Z'
        );
        INSERT INTO part VALUES (
            'p-2', 'msg-2', 'text',
            'Of course! What do you need?',
            NULL, NULL, '2024-06-01T10:00:05Z'
        );
    """
    )
    conn.commit()
    conn.close()


def _create_json_fallback(storage_dir: Path) -> None:
    """Create JSON fallback files matching OpenCode storage format."""
    (storage_dir / "session").mkdir(parents=True, exist_ok=True)
    (storage_dir / "message").mkdir(parents=True, exist_ok=True)
    (storage_dir / "part").mkdir(parents=True, exist_ok=True)

    sess = {
        "id": "sess-json-1",
        "path": "/home/user/project2",
        "title": "JSON Session",
        "createdAt": "2024-06-02T10:00:00Z",
        "updatedAt": "2024-06-02T10:05:00Z",
    }
    (storage_dir / "session" / "sess-json-1.json").write_text(
        json.dumps(sess)
    )

    msg1 = {
        "id": "msg-j1",
        "sessionID": "sess-json-1",
        "role": "user",
        "createdAt": "2024-06-02T10:00:00Z",
    }
    msg2 = {
        "id": "msg-j2",
        "sessionID": "sess-json-1",
        "role": "assistant",
        "createdAt": "2024-06-02T10:00:05Z",
    }
    (storage_dir / "message" / "msg-j1.json").write_text(
        json.dumps(msg1)
    )
    (storage_dir / "message" / "msg-j2.json").write_text(
        json.dumps(msg2)
    )

    part1 = {
        "id": "p-j1",
        "messageID": "msg-j1",
        "type": "text",
        "content": "Hi from JSON",
        "createdAt": "2024-06-02T10:00:00Z",
    }
    part2 = {
        "id": "p-j2",
        "messageID": "msg-j2",
        "type": "text",
        "content": "Hello!",
        "createdAt": "2024-06-02T10:00:05Z",
    }
    (storage_dir / "part" / "p-j1.json").write_text(
        json.dumps(part1)
    )
    (storage_dir / "part" / "p-j2.json").write_text(
        json.dumps(part2)
    )


def test_opencode_sqlite_parse(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_test_db(db_path)
    parser = OpenCodeParser(db_path=db_path)
    results = parser.parse_all()
    assert len(results) == 1
    r = results[0]
    assert r.canonical.source == "opencode"
    assert r.canonical.total_messages == 2
    assert r.canonical.user_messages == 1
    assert r.canonical.assistant_messages == 1


def test_opencode_dual_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_test_db(db_path)
    parser = OpenCodeParser(db_path=db_path)
    results = parser.parse_all()
    r = results[0]
    assert r.canonical is not None
    assert r.raw is not None
    assert r.raw.source == "opencode"


def test_opencode_message_content(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_test_db(db_path)
    parser = OpenCodeParser(db_path=db_path)
    results = parser.parse_all()
    msgs = results[0].canonical.messages
    assert msgs[0].role == "user"
    assert "Hello" in msgs[0].content
    assert msgs[1].role == "assistant"


def test_opencode_json_fallback(tmp_path: Path) -> None:
    storage_dir = tmp_path / "storage"
    _create_json_fallback(storage_dir)
    # No DB file — should fall back to JSON
    parser = OpenCodeParser(
        db_path=tmp_path / "nonexistent.db",
        storage_dir=storage_dir,
    )
    results = parser.parse_all()
    assert len(results) == 1
    assert results[0].canonical.source == "opencode"


def test_opencode_empty_db(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE session (
            id TEXT PRIMARY KEY, path TEXT, title TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE message (
            id TEXT PRIMARY KEY, session_id TEXT,
            role TEXT, created_at TEXT
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY, message_id TEXT,
            type TEXT, content TEXT, tool_name TEXT,
            tool_call_id TEXT, created_at TEXT
        );
    """
    )
    conn.commit()
    conn.close()
    parser = OpenCodeParser(db_path=db_path)
    results = parser.parse_all()
    assert len(results) == 0
