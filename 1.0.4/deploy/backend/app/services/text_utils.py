from __future__ import annotations

import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def normalize_vietnamese_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    compact = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", compact).strip()


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _split_sections(text: str) -> list[str]:
    lines = clean_text(text).split("\n")
    sections: list[str] = []
    current: list[str] = []
    heading_pattern = re.compile(r"^(#{1,6}\s+|\d+(\.\d+)*\s+|Điều\s+\d+|Khoản\s+\d+|Mục\s+\d+|[A-ZĐ][^.!?]{0,90}:$)")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current and current[-1] != "":
                current.append("")
            continue
        if current and heading_pattern.match(stripped):
            sections.append("\n".join(current).strip())
            current = [stripped]
        else:
            current.append(stripped)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。])\s+|\n{2,}", text)
    return [part.strip() for part in parts if part.strip()]


def split_chunks(text: str, chunk_size: int = 1100, overlap: int = 140) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []

    chunks: list[str] = []
    for section in _split_sections(normalized):
        if len(section) <= chunk_size:
            chunks.append(section)
            continue
        current = ""
        for sentence in _sentences(section):
            candidate = f"{current} {sentence}".strip()
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current.strip())
                prefix = current[-overlap:].strip() if overlap > 0 else ""
                current = f"{prefix} {sentence}".strip()
            else:
                for index in range(0, len(sentence), max(1, chunk_size - overlap)):
                    chunks.append(sentence[index : index + chunk_size].strip())
                current = ""
        if current:
            chunks.append(current.strip())

    compact_chunks: list[str] = []
    for chunk in chunks:
        cleaned = re.sub(r"\n{3,}", "\n\n", chunk).strip()
        if cleaned and cleaned not in compact_chunks:
            compact_chunks.append(cleaned)
    return compact_chunks
