from __future__ import annotations

from src.core.chunking import chunk_message


class TestChunkMessage:
    """Tests for chunk_message."""

    def test_empty_string(self) -> None:
        assert chunk_message("") == []

    def test_short_content_single_chunk(self) -> None:
        result = chunk_message("Hello, world!")
        assert result == ["Hello, world!"]

    def test_default_chunk_size(self) -> None:
        # Default should be CHUNK_SIZE (2000)
        content = "x" * 1999
        result = chunk_message(content)
        assert len(result) == 1

    def test_paragraph_boundary_split(self) -> None:
        para1 = "First paragraph. " * 50  # ~850 chars
        para2 = "Second paragraph. " * 50
        para3 = "Third paragraph. " * 50
        content = f"{para1}\n\n{para2}\n\n{para3}"
        result = chunk_message(content, chunk_size=1000)
        # Should split at paragraph boundaries
        assert len(result) >= 2
        # All content preserved (no truncation)
        reassembled = "".join(result)
        assert len(reassembled) == len(content)

    def test_no_content_lost(self) -> None:
        """All content must be indexed — nothing truncated."""
        para1 = "A" * 500
        para2 = "B" * 500
        para3 = "C" * 500
        content = f"{para1}\n\n{para2}\n\n{para3}"
        result = chunk_message(content, chunk_size=600)
        reassembled = "".join(result)
        assert reassembled == content

    def test_single_paragraph_exceeds_chunk_splits_at_sentences(self) -> None:
        # A single paragraph with multiple sentences that exceeds chunk_size
        sentences = "This is a sentence. " * 60  # ~1200 chars
        result = chunk_message(sentences, chunk_size=500)
        assert len(result) >= 2
        reassembled = "".join(result)
        assert reassembled == sentences

    def test_single_sentence_exceeds_chunk_hard_splits(self) -> None:
        # A single long sentence with no period breaks
        long_sentence = "a" * 3000
        result = chunk_message(long_sentence, chunk_size=1000)
        assert len(result) == 3
        assert result[0] == "a" * 1000
        assert result[1] == "a" * 1000
        assert result[2] == "a" * 1000
        assert "".join(result) == long_sentence

    def test_mixed_paragraphs(self) -> None:
        short_para = "Short."
        long_para = "Word " * 500  # 2500 chars
        content = f"{short_para}\n\n{long_para}"
        result = chunk_message(content, chunk_size=1000)
        reassembled = "".join(result)
        assert reassembled == content

    def test_multiple_newlines_treated_as_paragraph_break(self) -> None:
        content = "Para one.\n\n\n\nPara two."
        result = chunk_message(content, chunk_size=2000)
        # Content fits in one chunk
        assert len(result) == 1
        assert result[0] == content

    def test_whitespace_only_returns_empty(self) -> None:
        assert chunk_message("   ") == []
        assert chunk_message("\n\n\n") == []

    def test_custom_chunk_size(self) -> None:
        content = "Hello. " * 100
        result = chunk_message(content, chunk_size=100)
        for chunk in result:
            assert len(chunk) <= 100 or chunk.count(".") <= 1
        reassembled = "".join(result)
        assert reassembled == content

    def test_sentence_boundary_detection(self) -> None:
        # Sentences ending with ., !, ?
        content = "First sentence. Second sentence! Third sentence? Fourth sentence."
        result = chunk_message(content, chunk_size=40)
        assert len(result) >= 2
        reassembled = "".join(result)
        assert reassembled == content
