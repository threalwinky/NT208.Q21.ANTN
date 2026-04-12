from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class SourceType(str, Enum):
    OFFICIAL = "OFFICIAL"
    REFERENCE = "REFERENCE"


class CrawlStatus(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ContentCategoryCode(str, Enum):
    ACADEMIC = "ACADEMIC"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    SCHEDULE = "SCHEDULE"
    EXAM = "EXAM"
    TUITION = "TUITION"
    SCHOLARSHIP = "SCHOLARSHIP"
    WELLBEING = "WELLBEING"
    SKILL = "SKILL"
    PROCEDURE = "PROCEDURE"
    OTHER = "OTHER"


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ContentCategory(Base, TimestampMixin):
    __tablename__ = "content_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[ContentCategoryCode] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_official_uit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=720, nullable=False)
    settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    documents: Mapped[list["CollectedDocument"]] = relationship(back_populates="data_source")
    crawl_logs: Mapped[list["CrawlerLog"]] = relationship(back_populates="data_source")


class CollectedDocument(Base, TimestampMixin):
    __tablename__ = "collected_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("content_categories.id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_source_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(String(20), default=ConfidenceLevel.HIGH, nullable=False)
    is_official_uit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_wellbeing_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_academic_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vector_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    data_source: Mapped["DataSource | None"] = relationship(back_populates="documents")
    category: Mapped["ContentCategory | None"] = relationship()
    department: Mapped["Department | None"] = relationship()
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("collected_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped["CollectedDocument"] = relationship(back_populates="chunks")


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    group_name: Mapped[str] = mapped_column(String(60), nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("collected_documents.id"), nullable=True)
    is_official_uit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    document: Mapped["CollectedDocument | None"] = relationship()


class CrawlerLog(Base, TimestampMixin):
    __tablename__ = "crawler_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    status: Mapped[CrawlStatus] = mapped_column(String(30), default=CrawlStatus.READY, nullable=False)
    total_urls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    data_source: Mapped["DataSource"] = relationship(back_populates="crawl_logs")


class FAQ(Base, TimestampMixin):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    group_name: Mapped[str] = mapped_column(String(60), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SupportResource(Base, TimestampMixin):
    __tablename__ = "support_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_unit: Mapped[str | None] = mapped_column(String(150), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_official_uit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    urgent_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

