from __future__ import annotations

import re

from src.core.constants import CHUNK_SIZE


def chunk_message(content: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Split message content into chunks for full-text search indexing.

    Strategy:
    1. Split at paragraph boundaries (\\n\\n)
    2. If a single paragraph exceeds chunk_size, split at sentence boundaries
    3. If a single sentence exceeds chunk_size, hard split at chunk_size

    All content is preserved — nothing is truncated.
    """
    if not content or not content.strip():
        return []

    # Split into paragraphs at double-newline boundaries
    paragraphs = re.split(r"(\n\n+)", content)

    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        # Check if adding this paragraph would exceed chunk_size
        if current_chunk and len(current_chunk) + len(paragraph) > chunk_size:
            # Flush the current chunk
            chunks.append(current_chunk)
            current_chunk = ""

        if len(paragraph) <= chunk_size:
            current_chunk += paragraph
        else:
            # Paragraph exceeds chunk_size — split at sentence boundaries
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            _split_paragraph(paragraph, chunk_size, chunks)

    # Flush remaining content
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_paragraph(paragraph: str, chunk_size: int, chunks: list[str]) -> None:
    """Split a single paragraph at sentence boundaries, falling back to hard split."""
    # Use capturing group to preserve the whitespace separators between sentences.
    # This produces alternating [sentence_with_punct, whitespace, sentence, ...] segments.
    parts = re.split(r"([.!?])(\s+)", paragraph)

    # Reassemble into "sentence" units that include their trailing punctuation + whitespace.
    # parts pattern: [text, punct, ws, text, punct, ws, ..., text]
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        piece = parts[i]
        # Attach trailing punctuation and whitespace if they follow
        if i + 2 < len(parts):
            piece += parts[i + 1] + parts[i + 2]  # punct + whitespace
            i += 3
        else:
            i += 1
        if piece:
            sentences.append(piece)

    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > chunk_size:
            chunks.append(current)
            current = ""

        if len(sentence) <= chunk_size:
            current += sentence
        else:
            # Single sentence exceeds chunk_size — hard split
            if current:
                chunks.append(current)
                current = ""
            _hard_split(sentence, chunk_size, chunks)

    if current:
        chunks.append(current)


def _hard_split(text: str, chunk_size: int, chunks: list[str]) -> None:
    """Hard split text at exactly chunk_size boundaries."""
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i : i + chunk_size])
