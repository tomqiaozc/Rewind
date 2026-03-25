"""File change detection — inode + mtime + size triple-check."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class FileIdentity:
    """Immutable file identity snapshot."""

    inode: int
    mtime: float
    size: int

    def matches(self, other: FileIdentity) -> bool:
        """A file is unchanged only when ALL THREE match."""
        return (
            self.inode == other.inode
            and self.mtime == other.mtime
            and self.size == other.size
        )


def get_file_identity(path: Path) -> FileIdentity:
    """Get the current identity of a file.

    Raises FileNotFoundError if the file does not exist.
    """
    stat = os.stat(path)
    return FileIdentity(
        inode=stat.st_ino,
        mtime=stat.st_mtime,
        size=stat.st_size,
    )
