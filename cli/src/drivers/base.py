"""Base driver protocol."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDriver(ABC):
    """Abstract base for file and DB drivers."""

    @abstractmethod
    def read_incremental(self) -> tuple[Any, Any]:
        """Read new data since last cursor position.

        Returns (data, new_cursor_state).
        """
        ...
