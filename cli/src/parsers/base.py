"""Parser base protocol — all parsers must implement this."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.config.cursors import FileCursor
    from src.core.types import CanonicalSession, RawSessionArchive


@dataclass
class ParseResult:
    """Result of parsing a single session."""
    canonical: CanonicalSession
    raw: RawSessionArchive
    cursor_key: str  # unique key for cursor tracking
    cursor: Optional[FileCursor] = None  # new cursor state to save on upload success
    errors: list[str] = field(default_factory=list)


@dataclass
class ParseError:
    """A parse error that was logged but not fatal."""
    source: str
    file_path: str
    message: str
    details: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for source parsers."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"rewind.parser.{self.source_name}")
        self.errors: list[ParseError] = []

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier (e.g., 'claude', 'opencode', 'gemini')."""
        ...

    @abstractmethod
    def discover(self) -> list[Path]:
        """Discover all session files/databases for this source.

        Returns a list of paths to session files or databases.
        """
        ...

    @abstractmethod
    def parse_all(self) -> list[ParseResult]:
        """Discover and parse all sessions, returning ParseResults.

        Must produce dual output (CanonicalSession + RawSessionArchive).
        Parse errors are logged, never silently dropped.
        """
        ...

    def log_error(self, file_path: str, message: str, details: Optional[str] = None) -> None:
        """Log a parse error — never silently drop."""
        error = ParseError(
            source=self.source_name,
            file_path=file_path,
            message=message,
            details=details,
        )
        self.errors.append(error)
        self.logger.warning("Parse error in %s: %s", file_path, message)
