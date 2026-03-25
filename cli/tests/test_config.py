"""Tests for config manager."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.config.cursors import CursorStore, FileCursor
from src.config.manager import ConfigManager

if TYPE_CHECKING:
    from pathlib import Path


def test_default_config(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    assert mgr.api_url is None
    assert mgr.api_key is None
    assert mgr.device_id is not None  # auto-generated UUID


def test_save_and_load(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    mgr.api_url = "https://api.example.com"
    mgr.api_key = "rw_test123"
    mgr.save()

    mgr2 = ConfigManager(config_dir=tmp_path)
    assert mgr2.api_url == "https://api.example.com"
    assert mgr2.api_key == "rw_test123"
    assert mgr2.device_id == mgr.device_id


def test_config_file_created(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    mgr.api_url = "https://api.example.com"
    mgr.save()
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text())
    assert data["api_url"] == "https://api.example.com"


def test_is_authenticated(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    assert not mgr.is_authenticated
    mgr.api_url = "https://api.example.com"
    mgr.api_key = "rw_test123"
    assert mgr.is_authenticated


# --- Cursor state persistence tests ---


def test_cursor_store_empty(tmp_path: Path) -> None:
    store = CursorStore(config_dir=tmp_path)
    assert store.get("nonexistent") is None


def test_cursor_save_and_load(tmp_path: Path) -> None:
    store = CursorStore(config_dir=tmp_path)
    cursor = FileCursor(inode=12345, mtime=1700000000.0, size=4096, byte_offset=2048)
    store.set("claude:/home/user/.claude/projects/foo/abc.jsonl", cursor)
    store.save()

    store2 = CursorStore(config_dir=tmp_path)
    loaded = store2.get("claude:/home/user/.claude/projects/foo/abc.jsonl")
    assert loaded is not None
    assert loaded.byte_offset == 2048
    assert loaded.inode == 12345


def test_cursor_rollback(tmp_path: Path) -> None:
    store = CursorStore(config_dir=tmp_path)
    cursor = FileCursor(inode=12345, mtime=1700000000.0, size=4096, byte_offset=2048)
    store.set("key1", cursor)
    store.save()

    # Update cursor
    store.set("key1", FileCursor(inode=12345, mtime=1700000001.0, size=5000, byte_offset=4000))
    # Rollback without saving
    store.rollback("key1")
    current = store.get("key1")
    assert current is not None
    assert current.byte_offset == 2048  # reverted to saved state


def test_cursor_file_changed_detection(tmp_path: Path) -> None:
    store = CursorStore(config_dir=tmp_path)
    cursor = FileCursor(inode=12345, mtime=1700000000.0, size=4096, byte_offset=2048)
    store.set("key1", cursor)
    # Different inode = file changed, cursor should be invalidated
    assert cursor.file_matches(inode=99999, mtime=1700000000.0, size=4096) is False
    assert cursor.file_matches(inode=12345, mtime=1700000000.0, size=4096) is True
