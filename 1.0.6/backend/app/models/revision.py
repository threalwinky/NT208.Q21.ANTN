from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class RevisionDocStatus(str, Enum):
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class Notebook(Base, TimestampMixin):
    """Sổ ôn tập cá nhân của sinh viên (tách biệt hoàn toàn với corpus UIT)."""

    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    documents: Mapped[list["NotebookDocument"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )


class NotebookDocument(Base, TimestampMixin):
    """Tài liệu PDF sinh viên tải lên một notebook. Chunk/vector nằm trong
    collection Qdrant riêng (studify_revision), lọc theo notebook_id."""

    __tablename__ = "notebook_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RevisionDocStatus.PROCESSING.value, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped["Notebook"] = relationship(back_populates="documents")
