"""Cursor state persistence — tracks per-file sync progress."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileCursor:
    """Cursor for flat files (JSONL/JSON)."""

    inode: int
    mtime: float
    size: int
    byte_offset: int = 0
    array_index: int = 0  # for JSON array files (Gemini)
    watermark: Optional[str] = None  # for DB sources (OpenCode)

    def file_matches(self, inode: int, mtime: float, size: int) -> bool:
        """Triple-check: file is unchanged only when ALL THREE match."""
        return self.inode == inode and self.mtime == mtime and self.size == size


class CursorStore:
    """Manages cursor state for all tracked files/sources."""

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._cursor_file = self._config_dir / "cursors.json"
        self._cursors: dict[str, FileCursor] = {}
        self._saved: dict[str, FileCursor] = {}  # snapshot for rollback
        self._load()

    def _load(self) -> None:
        if self._cursor_file.exists():
            data = json.loads(self._cursor_file.read_text())
            for key, val in data.items():
                self._cursors[key] = FileCursor(**val)
            # Snapshot for rollback
            self._saved = {k: FileCursor(**asdict(v)) for k, v in self._cursors.items()}

    def save(self) -> None:
        data = {k: asdict(v) for k, v in self._cursors.items()}
        self._cursor_file.write_text(json.dumps(data, indent=2) + "\n")
        self._saved = {k: FileCursor(**asdict(v)) for k, v in self._cursors.items()}

    def get(self, key: str) -> Optional[FileCursor]:
        return self._cursors.get(key)

    def set(self, key: str, cursor: FileCursor) -> None:
        self._cursors[key] = cursor

    def rollback(self, key: str) -> None:
        """Revert a cursor to its last-saved state."""
        if key in self._saved:
            self._cursors[key] = FileCursor(**asdict(self._saved[key]))
        else:
            self._cursors.pop(key, None)

    def all_keys(self) -> list[str]:
        return list(self._cursors.keys())
