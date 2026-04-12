from __future__ import annotations

import hashlib
import re


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def split_chunks(text: str, chunk_size: int = 900, overlap: int = 180) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start += step
    return chunks

