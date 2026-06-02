from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    title: str
    url: str
    group_name: str | None = None
    summary: str | None = None
    file_type: str | None = None
    is_official_uit: bool
    is_academic_related: bool
    is_wellbeing_related: bool
    tags: list[str] = []
    published_at: datetime | None = None
    updated_source_at: datetime | None = None


class DocumentChunkOut(BaseModel):
    id: int
    chunk_index: int
    content: str
    char_count: int


class DocumentDetailOut(DocumentOut):
    cleaned_content: str | None = None
    chunks: list[DocumentChunkOut] = []
