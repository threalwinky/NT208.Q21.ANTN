from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DataSourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    domain: str
    source_type: str
    is_enabled: bool
    is_official_uit: bool
    crawl_interval_minutes: int


class CrawlerLogOut(BaseModel):
    id: int
    data_source_id: int
    status: str
    total_urls: int
    new_documents: int
    updated_documents: int
    error_count: int
    message: str | None = None
    created_at: datetime


class UpdateDataSourceRequest(BaseModel):
    is_enabled: bool


class UpdateConfigRequest(BaseModel):
    key: str
    value_json: dict
    description: str | None = None

