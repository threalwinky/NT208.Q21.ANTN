from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CitationItem(BaseModel):
    document_id: int
    title: str
    url: str
    source_label: str
    confidence: str
    excerpt: str
    updated_at: datetime | None = None


class SendMessageRequest(BaseModel):
    session_id: int | None = None
    content: str


class ChatMessageItem(BaseModel):
    id: int
    role: str
    category: str | None = None
    content: str
    created_at: datetime
    risk_score: float = 0
    is_urgent: bool = False


class ChatSessionOut(BaseModel):
    id: int
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageItem] = []


class ChatReply(BaseModel):
    session_id: int
    category: str
    answer: str
    is_urgent: bool
    risk_score: float
    citations: list[CitationItem]
    action_suggestions: list[str]
