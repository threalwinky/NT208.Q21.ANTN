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
    detail_json: dict | None = None
    created_at: datetime


class AdminRuntimeOut(BaseModel):
    queue_size: int
    refresh_schedule: dict
    refresh_runtime: dict


class AdminDocumentOut(BaseModel):
    id: int
    title: str
    url: str
    group_name: str | None = None
    file_type: str | None = None
    is_official_uit: bool
    updated_source_at: datetime | None = None
    vector_metadata: dict | None = None


class AdminUploadOut(BaseModel):
    document_id: int
    title: str
    status: str
    chunk_count: int
    used_ocr: bool
    group_name: str
    file_type: str
    is_official_uit: bool
    url: str


class UpdateDataSourceRequest(BaseModel):
    is_enabled: bool


class UpdateConfigRequest(BaseModel):
    key: str
    value_json: dict
    description: str | None = None
