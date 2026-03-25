"""Tests for file change detection utility."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from src.utils.file_identity import FileIdentity, get_file_identity


def test_get_file_identity(tmp_path: Path) -> None:
    f = tmp_path / "test.jsonl"
    f.write_text('{"hello": "world"}\n')
    identity = get_file_identity(f)
    assert identity.inode > 0
    assert identity.mtime > 0
    assert identity.size == len(f.read_bytes())


def test_identity_unchanged(tmp_path: Path) -> None:
    f = tmp_path / "test.jsonl"
    f.write_text('{"hello": "world"}\n')
    id1 = get_file_identity(f)
    id2 = get_file_identity(f)
    assert id1.matches(id2)


def test_identity_changed_content(tmp_path: Path) -> None:
    f = tmp_path / "test.jsonl"
    f.write_text('{"hello": "world"}\n')
    id1 = get_file_identity(f)
    time.sleep(0.05)  # ensure mtime changes
    f.write_text('{"hello": "world"}\n{"another": "line"}\n')
    id2 = get_file_identity(f)
    # Size changed → not matching
    assert not id1.matches(id2)


def test_identity_changed_inode(tmp_path: Path) -> None:
    f = tmp_path / "test.jsonl"
    f.write_text("content")
    id1 = get_file_identity(f)
    # Delete and recreate → new inode
    f.unlink()
    f.write_text("content")
    id2 = get_file_identity(f)
    # On most filesystems, inode changes on delete+recreate
    # If same inode (rare), at least mtime differs
    if id1.inode != id2.inode:
        assert not id1.matches(id2)


def test_identity_from_values() -> None:
    identity = FileIdentity(inode=123, mtime=1700000000.0, size=4096)
    assert identity.inode == 123
    assert identity.mtime == 1700000000.0
    assert identity.size == 4096
