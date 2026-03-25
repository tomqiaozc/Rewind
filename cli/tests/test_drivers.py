"""Tests for FileDriver and DbDriver."""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from src.config.cursors import CursorStore, FileCursor
from src.drivers.db_driver import DbDriver
from src.drivers.file_driver import FileDriver

if TYPE_CHECKING:
    from pathlib import Path


def test_file_driver_read_new_file(tmp_path: Path) -> None:
    """FileDriver reads entire file when no cursor exists."""
    f = tmp_path / "session.jsonl"
    lines = ['{"type":"user","content":"hello"}\n', '{"type":"assistant","content":"hi"}\n']
    f.write_text("".join(lines))
    store = CursorStore(config_dir=tmp_path / "config")

    driver = FileDriver(path=f, cursor_store=store, cursor_key="test:session.jsonl")
    data, new_cursor = driver.read_incremental()
    assert len(data) == 2
    assert new_cursor.byte_offset == f.stat().st_size


def test_file_driver_incremental_read(tmp_path: Path) -> None:
    """FileDriver reads only new bytes after cursor."""
    f = tmp_path / "session.jsonl"
    line1 = '{"type":"user","content":"hello"}\n'
    f.write_text(line1)
    store = CursorStore(config_dir=tmp_path / "config")

    driver = FileDriver(path=f, cursor_store=store, cursor_key="test:session.jsonl")
    data1, cursor1 = driver.read_incremental()
    assert len(data1) == 1
    store.set("test:session.jsonl", cursor1)
    store.save()

    # Append a new line
    line2 = '{"type":"assistant","content":"hi"}\n'
    with open(f, "a") as fh:
        fh.write(line2)

    store2 = CursorStore(config_dir=tmp_path / "config")
    driver2 = FileDriver(path=f, cursor_store=store2, cursor_key="test:session.jsonl")
    data2, cursor2 = driver2.read_incremental()
    assert len(data2) == 1  # only the new line
    assert data2[0]["type"] == "assistant"


def test_file_driver_file_replaced(tmp_path: Path) -> None:
    """FileDriver re-reads entire file when inode changes."""
    f = tmp_path / "session.jsonl"
    f.write_text('{"type":"user","content":"v1"}\n')
    store = CursorStore(config_dir=tmp_path / "config")

    driver = FileDriver(path=f, cursor_store=store, cursor_key="test:session.jsonl")
    _, cursor = driver.read_incremental()
    store.set("test:session.jsonl", cursor)
    store.save()

    # Replace file (delete + create = new inode)
    f.unlink()
    f.write_text('{"type":"user","content":"v2"}\n{"type":"assistant","content":"reply"}\n')

    store2 = CursorStore(config_dir=tmp_path / "config")
    driver2 = FileDriver(path=f, cursor_store=store2, cursor_key="test:session.jsonl")
    data, _ = driver2.read_incremental()
    # Should read entire file since inode changed
    assert len(data) >= 1


def test_db_driver_read_all(tmp_path: Path) -> None:
    """DbDriver reads all rows when no watermark."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE session (id TEXT, created TEXT)")
    conn.execute("INSERT INTO session VALUES ('s1', '2024-01-01T00:00:00Z')")
    conn.execute("INSERT INTO session VALUES ('s2', '2024-01-02T00:00:00Z')")
    conn.commit()
    conn.close()

    store = CursorStore(config_dir=tmp_path / "config")
    driver = DbDriver(
        db_path=db_path,
        cursor_store=store,
        cursor_key="opencode:db",
        table="session",
        id_column="id",
        watermark_column="created",
    )
    rows, new_watermark = driver.read_incremental()
    assert len(rows) == 2
    assert new_watermark == "2024-01-02T00:00:00Z"


def test_db_driver_incremental(tmp_path: Path) -> None:
    """DbDriver reads only rows after watermark."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE session (id TEXT, created TEXT)")
    conn.execute("INSERT INTO session VALUES ('s1', '2024-01-01T00:00:00Z')")
    conn.commit()
    conn.close()

    store = CursorStore(config_dir=tmp_path / "config")
    driver = DbDriver(
        db_path=db_path,
        cursor_store=store,
        cursor_key="opencode:db",
        table="session",
        id_column="id",
        watermark_column="created",
    )
    _, wm = driver.read_incremental()

    # Set watermark cursor
    from src.utils.file_identity import get_file_identity

    identity = get_file_identity(db_path)
    cursor = FileCursor(
        inode=identity.inode, mtime=identity.mtime, size=identity.size, watermark=wm,
    )
    store.set("opencode:db", cursor)
    store.save()

    # Add new row
    conn2 = sqlite3.connect(str(db_path))
    conn2.execute("INSERT INTO session VALUES ('s2', '2024-01-02T00:00:00Z')")
    conn2.commit()
    conn2.close()

    store2 = CursorStore(config_dir=tmp_path / "config")
    driver2 = DbDriver(
        db_path=db_path,
        cursor_store=store2,
        cursor_key="opencode:db",
        table="session",
        id_column="id",
        watermark_column="created",
    )
    rows, _ = driver2.read_incremental()
    assert len(rows) == 1
    assert rows[0]["id"] == "s2"
