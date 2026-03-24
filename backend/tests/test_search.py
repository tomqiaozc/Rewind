"""Tests for the search service — sanitize_snippet unit tests.

NOTE: search_sessions() relies on PostgreSQL's tsvector/tsquery and cannot
be tested against SQLite. Only the pure-Python sanitize_snippet() helper is
tested here.
"""
from __future__ import annotations

from src.services.search import SNIPPET_CLOSE, SNIPPET_OPEN, sanitize_snippet

# ---------------------------------------------------------------------------
# sanitize_snippet unit tests
# ---------------------------------------------------------------------------


class TestSanitizeSnippet:
    """Tests for the sanitize_snippet helper."""

    def test_sanitize_snippet_basic(self) -> None:
        """Control-char delimiters are replaced with <mark> tags."""
        raw = f"some text {SNIPPET_OPEN}highlighted{SNIPPET_CLOSE} more text"
        result = sanitize_snippet(raw)
        assert result == "some text <mark>highlighted</mark> more text"

    def test_sanitize_snippet_xss(self) -> None:
        """HTML inside the content is escaped BEFORE mark tags are inserted."""
        raw = (
            f"before <script>alert('xss')</script> "
            f"{SNIPPET_OPEN}match{SNIPPET_CLOSE} after"
        )
        result = sanitize_snippet(raw)
        # The <script> tag must be escaped
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        # But <mark> tags must be present (not escaped)
        assert "<mark>match</mark>" in result

    def test_sanitize_snippet_empty(self) -> None:
        """Empty string returns empty string."""
        assert sanitize_snippet("") == ""

    def test_sanitize_snippet_no_markers(self) -> None:
        """String without control-char markers is just HTML-escaped."""
        raw = "plain text with <b>bold</b> & 'quotes'"
        result = sanitize_snippet(raw)
        assert result == "plain text with &lt;b&gt;bold&lt;/b&gt; &amp; &#x27;quotes&#x27;"
        assert "<mark>" not in result

    def test_sanitize_snippet_multiple_highlights(self) -> None:
        """Multiple highlighted segments are all converted."""
        raw = (
            f"{SNIPPET_OPEN}first{SNIPPET_CLOSE} middle "
            f"{SNIPPET_OPEN}second{SNIPPET_CLOSE}"
        )
        result = sanitize_snippet(raw)
        assert result == "<mark>first</mark> middle <mark>second</mark>"

    def test_sanitize_snippet_adjacent_highlights(self) -> None:
        """Adjacent highlights with no space between them."""
        raw = f"{SNIPPET_OPEN}foo{SNIPPET_CLOSE}{SNIPPET_OPEN}bar{SNIPPET_CLOSE}"
        result = sanitize_snippet(raw)
        assert result == "<mark>foo</mark><mark>bar</mark>"

    def test_sanitize_snippet_html_inside_highlight(self) -> None:
        """HTML entities inside highlighted text are escaped."""
        raw = f"{SNIPPET_OPEN}<div>code</div>{SNIPPET_CLOSE}"
        result = sanitize_snippet(raw)
        assert result == "<mark>&lt;div&gt;code&lt;/div&gt;</mark>"

    def test_sanitize_snippet_ampersand_handling(self) -> None:
        """Ampersands are properly escaped."""
        raw = f"a & b {SNIPPET_OPEN}c & d{SNIPPET_CLOSE}"
        result = sanitize_snippet(raw)
        assert "a &amp; b" in result
        assert "<mark>c &amp; d</mark>" in result
