from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class MoodState(Base, TimestampMixin):
    __tablename__ = "mood_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    intensity: Mapped[int] = mapped_column(Integer, default=3, nullable=False)


class MoodJournal(Base, TimestampMixin):
    __tablename__ = "mood_journals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mood_state_id: Mapped[int | None] = mapped_column(ForeignKey("mood_states.id"), nullable=True)
    short_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    energy_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    hide_from_dashboard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_soft_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_human_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    mood_state: Mapped["MoodState | None"] = relationship()


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SavedAnnouncement(Base, TimestampMixin):
    __tablename__ = "saved_announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    announcement_id: Mapped[int] = mapped_column(ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class InAppNotification(Base, TimestampMixin):
    __tablename__ = "in_app_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
