"""FileDriver — reads flat files (JSONL/JSON) incrementally using byte-offset cursors."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.drivers.base import BaseDriver
from src.utils.file_identity import get_file_identity

if TYPE_CHECKING:
    from src.config.cursors import CursorStore

from src.config.cursors import FileCursor


class FileDriver(BaseDriver):
    """Reads JSONL files incrementally using byte-offset cursors."""

    def __init__(
        self,
        path: Path,
        cursor_store: CursorStore,
        cursor_key: str,
    ) -> None:
        self.path = path
        self._cursor_store = cursor_store
        self._cursor_key = cursor_key

    def read_incremental(self) -> tuple[list[dict[str, Any]], FileCursor]:
        """Read new JSONL lines since last byte offset.

        Returns (list_of_parsed_json_objects, new_cursor).
        If file identity changed (inode/mtime/size mismatch), re-reads from start.
        """
        identity = get_file_identity(self.path)
        existing = self._cursor_store.get(self._cursor_key)

        offset = 0
        if existing and existing.file_matches(
            inode=identity.inode, mtime=identity.mtime, size=identity.size
        ):
            # File unchanged — already fully processed
            return [], FileCursor(
                inode=identity.inode,
                mtime=identity.mtime,
                size=identity.size,
                byte_offset=existing.byte_offset,
            )

        if existing and existing.inode == identity.inode and identity.size > existing.size:
            # Same inode, file grew — resume from last offset
            offset = existing.byte_offset

        results: list[dict[str, Any]] = []
        with open(self.path, "rb") as f:
            f.seek(offset)
            for line in f:
                line_str = line.decode("utf-8", errors="replace").strip()
                if line_str:
                    try:
                        results.append(json.loads(line_str))
                    except json.JSONDecodeError:
                        continue
            new_offset = f.tell()

        new_cursor = FileCursor(
            inode=identity.inode,
            mtime=identity.mtime,
            size=identity.size,
            byte_offset=new_offset,
        )
        return results, new_cursor
