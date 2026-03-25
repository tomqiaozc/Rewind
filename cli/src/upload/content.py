"""Content upload helpers — gzip compression."""
from __future__ import annotations

import gzip
import hashlib
import json
from typing import Any


def compress_json(data: Any) -> bytes:
    """Serialize data to JSON and gzip-compress it."""
    json_bytes = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
    return gzip.compress(json_bytes)


def compute_hash(data: Any) -> str:
    """Compute SHA-256 hash of JSON-serialized data."""
    json_bytes = json.dumps(data, default=str, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
