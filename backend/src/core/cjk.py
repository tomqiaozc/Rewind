"""CJK character detection utilities for multilingual search."""

from __future__ import annotations

import re

# Unicode ranges covering CJK Unified Ideographs, Radicals, Kangxi,
# Hiragana, Katakana, Hangul Syllables, and common CJK extensions.
_CJK_RANGES = (
    r"\u2E80-\u9FFF"
    r"\uF900-\uFAFF"
    r"\uFE30-\uFE4F"
    r"\u3040-\u309F"
    r"\u30A0-\u30FF"
    r"\uAC00-\uD7AF"
)

_CJK_RE = re.compile(f"[{_CJK_RANGES}]")


def contains_cjk(text: str) -> bool:
    """Return True if *text* contains any CJK character."""
    return bool(_CJK_RE.search(text))


def extract_cjk_and_latin(query: str) -> tuple[str, str]:
    """Split *query* into a CJK portion and a Latin/ASCII portion.

    Returns ``(cjk_part, latin_part)`` where either may be empty.
    """
    cjk_chars: list[str] = []
    latin_chars: list[str] = []
    for ch in query:
        if _CJK_RE.match(ch):
            cjk_chars.append(ch)
        else:
            latin_chars.append(ch)
    return "".join(cjk_chars).strip(), "".join(latin_chars).strip()
