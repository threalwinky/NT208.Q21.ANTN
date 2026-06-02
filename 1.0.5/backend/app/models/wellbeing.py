from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
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


class MoodCheckin(Base, TimestampMixin):
    __tablename__ = "mood_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mood_code: Mapped[str] = mapped_column(String(40), nullable=False, default="neutral")
    valence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    stress: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    motivation: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    focus: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note_preview: Mapped[str | None] = mapped_column(String(255), nullable=True)
    needs_human_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class WellbeingNote(Base, TimestampMixin):
    __tablename__ = "wellbeing_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False, default="Ghi chú riêng")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mood_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_soft_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_human_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MusicPlaylist(Base, TimestampMixin):
    __tablename__ = "music_playlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    theme: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    spotify_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SpotifyAccount(Base, TimestampMixin):
    __tablename__ = "spotify_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    spotify_user_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    access_token_preview: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # OAuth tokens (Fernet-encrypted at rest)
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SpotifyPlaylistMapping(Base, TimestampMixin):
    __tablename__ = "spotify_playlist_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("music_playlists.id", ondelete="CASCADE"), nullable=False)
    mood_code: Mapped[str] = mapped_column(String(40), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class WellbeingRecommendation(Base, TimestampMixin):
    __tablename__ = "wellbeing_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


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
