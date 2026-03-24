from __future__ import annotations

import re

from src.core.constants import MAX_TITLE_LENGTH, SOURCE_TYPES


def validate_source(source: str) -> str:
    """Validate that source is one of the allowed SOURCE_TYPES.

    Raises ValueError if not valid.
    """
    if source not in SOURCE_TYPES:
        msg = f"Invalid source: {source!r}. Must be one of {SOURCE_TYPES}"
        raise ValueError(msg)
    return source


def validate_session_key(key: str) -> str:
    """Validate that session key is a non-empty string.

    Strips whitespace. Raises ValueError if empty or whitespace-only.
    """
    stripped = key.strip()
    if not stripped:
        msg = "Session key must be a non-empty string"
        raise ValueError(msg)
    return stripped


def build_title(
    project_name: str | None,
    first_user_message: str | None,
) -> str | None:
    """Build a session title from project name and first user message.

    - Uses [last_path_segment] as prefix if project_name is provided
    - Normalizes whitespace
    - Truncates on word boundary with "..." if exceeds MAX_TITLE_LENGTH
    - Returns None if both inputs are empty/None
    """
    # Normalize project segment
    prefix = ""
    if project_name and project_name.strip():
        # Extract last path segment, handle trailing slashes
        segment = project_name.rstrip("/").rsplit("/", 1)[-1].strip()
        if segment:
            prefix = f"[{segment}]"

    # Normalize message
    msg = ""
    if first_user_message and first_user_message.strip():
        # Normalize whitespace: replace newlines, tabs, multiple spaces with single space
        msg = re.sub(r"\s+", " ", first_user_message).strip()

    if not prefix and not msg:
        return None

    if prefix and msg:
        title = f"{prefix} {msg}"
    elif prefix:
        title = prefix
    else:
        title = msg

    if len(title) <= MAX_TITLE_LENGTH:
        return title

    # Truncate on word boundary
    truncated = title[: MAX_TITLE_LENGTH - 3]  # Reserve space for "..."
    # Find last space to break on word boundary
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."
