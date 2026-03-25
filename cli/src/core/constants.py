# SOURCE OF TRUTH: backend/src/core/constants.py
# This is a copy for CLI use. Keep in sync with the backend version.
from __future__ import annotations

PARSER_REVISION = 1
SCHEMA_VERSION = 1
API_KEY_PREFIX = "rw_"
MAX_TITLE_LENGTH = 80
MAX_CONTENT_SIZE_BYTES = 52_428_800  # 50 MB
MAX_DECOMPRESSED_SIZE_BYTES = 268_435_456  # 256 MB
MAX_METADATA_SIZE_BYTES = 2_097_152  # 2 MB
MAX_BATCH_SIZE = 50
CHUNK_SIZE = 2000  # chars per FTS chunk
SOURCE_TYPES = ("claude", "opencode", "gemini", "codex", "copilot")
