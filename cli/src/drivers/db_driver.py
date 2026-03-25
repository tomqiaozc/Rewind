"""DbDriver — reads SQLite databases incrementally using watermark cursors."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.config.cursors import CursorStore

from src.drivers.base import BaseDriver
from src.utils.file_identity import get_file_identity


class DbDriver(BaseDriver):
    """Reads SQLite databases incrementally using watermark cursors."""

    def __init__(
        self,
        db_path: Path,
        cursor_store: CursorStore,
        cursor_key: str,
        table: str,
        id_column: str,
        watermark_column: str,
    ) -> None:
        self.db_path = db_path
        self._cursor_store = cursor_store
        self._cursor_key = cursor_key
        self._table = table
        self._id_column = id_column
        self._watermark_column = watermark_column

    def read_incremental(self) -> tuple[list[dict[str, Any]], Optional[str]]:
        """Read rows since last watermark.

        Returns (list_of_row_dicts, new_watermark).
        If inode changed, re-reads everything (full rescan).
        """
        identity = get_file_identity(self.db_path)
        existing = self._cursor_store.get(self._cursor_key)

        watermark: Optional[str] = None
        if existing:
            watermark = None if existing.inode != identity.inode else existing.watermark

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            if watermark:
                query = (
                    f"SELECT * FROM {self._table} "
                    f"WHERE {self._watermark_column} > ? "
                    f"ORDER BY {self._watermark_column} ASC"
                )
                rows = conn.execute(query, (watermark,)).fetchall()
            else:
                query = (
                    f"SELECT * FROM {self._table} "
                    f"ORDER BY {self._watermark_column} ASC"
                )
                rows = conn.execute(query).fetchall()

            results = [dict(row) for row in rows]
            new_watermark = results[-1][self._watermark_column] if results else watermark
            return results, new_watermark
        finally:
            conn.close()
