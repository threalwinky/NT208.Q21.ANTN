from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    target_type: str = "general"
    target_id: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    message: str = Field(min_length=2)
    metadata_json: dict | None = None


class FeedbackUpdateRequest(BaseModel):
    status: str | None = None
    admin_note: str | None = None
    is_resolved: bool | None = None


class FeedbackOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    target_type: str
    target_id: str | None = None
    rating: int | None = None
    message: str
    status: str
    admin_note: str | None = None
    is_resolved: bool
    metadata_json: dict | None = None
    created_at: datetime
