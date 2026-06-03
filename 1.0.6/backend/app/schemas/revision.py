from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NotebookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class NotebookDocumentOut(BaseModel):
    id: int
    title: str
    filename: str
    status: str
    chunk_count: int
    char_count: int
    used_ocr: bool
    error: str | None = None
    created_at: datetime


class NotebookOut(BaseModel):
    id: int
    title: str
    document_count: int
    ready_count: int
    created_at: datetime
    updated_at: datetime


class NotebookDetailOut(NotebookOut):
    documents: list[NotebookDocumentOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class RevisionCitation(BaseModel):
    doc_title: str
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    citations: list[RevisionCitation]
