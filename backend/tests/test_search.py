"""Tests for the search service — sanitize_snippet and highlight_substring.

NOTE: search_sessions() relies on PostgreSQL's tsvector/tsquery and cannot
be tested against SQLite. Only the pure-Python helpers are tested here.
"""

from __future__ import annotations

from src.services.search import (
    SNIPPET_CLOSE,
    SNIPPET_OPEN,
    highlight_substring,
    sanitize_snippet,
)

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
        raw = f"before <script>alert('xss')</script> {SNIPPET_OPEN}match{SNIPPET_CLOSE} after"
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
        raw = f"{SNIPPET_OPEN}first{SNIPPET_CLOSE} middle {SNIPPET_OPEN}second{SNIPPET_CLOSE}"
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


# ---------------------------------------------------------------------------
# highlight_substring unit tests
# ---------------------------------------------------------------------------


class TestHighlightSubstring:
    """Tests for the CJK substring highlighting helper."""

    def test_basic_match(self) -> None:
        """Query found in content gets wrapped in <mark> tags."""
        result = highlight_substring("hello 用户认证 world", "用户认证")
        assert "<mark>用户认证</mark>" in result

    def test_case_insensitive(self) -> None:
        """Match is case-insensitive for Latin text."""
        result = highlight_substring("Hello World", "hello")
        assert "<mark>Hello</mark>" in result

    def test_xss_safe(self) -> None:
        """HTML in content is escaped, <mark> tags are safe."""
        result = highlight_substring("<script>alert('x')</script> 测试", "测试")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "<mark>测试</mark>" in result

    def test_not_found(self) -> None:
        """When query is not found, return escaped start of content."""
        result = highlight_substring("some content here", "不存在")
        assert "<mark>" not in result
        assert "some content here" in result

    def test_context_window(self) -> None:
        """Long content is trimmed to context around the match."""
        content = "A" * 200 + "匹配" + "B" * 200
        result = highlight_substring(content, "匹配", context_chars=10)
        assert "<mark>匹配</mark>" in result
        assert result.startswith("...")
        assert result.endswith("...")

    def test_match_at_start(self) -> None:
        """Match at the beginning of content — no leading ellipsis."""
        result = highlight_substring("测试内容后面很长", "测试")
        assert not result.startswith("...")
        assert "<mark>测试</mark>" in result

    def test_match_at_end(self) -> None:
        """Match at the end of content — no trailing ellipsis."""
        result = highlight_substring("前面的内容测试", "测试")
        assert not result.endswith("...")
        assert "<mark>测试</mark>" in result
