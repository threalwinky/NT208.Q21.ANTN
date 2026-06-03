from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MoodStateOut(BaseModel):
    id: int
    code: str
    display_name: str
    description: str | None = None
    color: str | None = None
    intensity: int


class MoodCheckinRequest(BaseModel):
    mood_state_id: int | None = None
    short_note: str | None = None
    energy_level: int = 3
    needs_human_support: bool = False


class EnergyInsightPreviewRequest(BaseModel):
    mood_state_id: int | None = None
    short_note: str | None = None


class MoodJournalOut(BaseModel):
    id: int
    short_note: str | None = None
    energy_level: int
    energy_label: str
    energy_summary: str
    signals: list[str] = []
    needs_human_support: bool
    created_at: datetime
    mood_label: str | None = None


class WellbeingRecommendationOut(BaseModel):
    kind: str
    title: str
    subtitle: str
    description: str
    url: str | None = None
    image_url: str | None = None


class MusicTrackOut(BaseModel):
    title: str
    artist: str
    album: str
    url: str
    embed_url: str
    image_url: str | None = None


class EnergyInsightOut(BaseModel):
    latest_energy_level: int
    latest_energy_label: str
    latest_mood_label: str | None = None
    average_energy_level: float
    trend: str
    summary: str
    signals: list[str] = []
    low_energy_threshold: float
    recommendation_mode: str
    recommendations: list[WellbeingRecommendationOut]
    music_theme: str = "focus"
    music_theme_label: str = "Tập trung nhẹ"
    music_tracks: list[MusicTrackOut] = []
    energy_series: list[int] = []


class SupportResourceOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    resource_type: str
    owner_unit: str | None = None
    link_url: str | None = None
    contact: str | None = None
    is_official_uit: bool
    urgent_priority: int


class WellbeingCheckinCreateRequest(BaseModel):
    mood_code: str = "neutral"
    valence: int = Field(default=3, ge=1, le=5)
    energy: int = Field(default=3, ge=1, le=5)
    stress: int = Field(default=3, ge=1, le=5)
    motivation: int = Field(default=3, ge=1, le=5)
    focus: int = Field(default=3, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    note_preview: str | None = None
    needs_human_support: bool = False
    safety_metadata: dict | None = None


class WellbeingCheckinOut(BaseModel):
    id: int
    mood_code: str
    valence: int
    energy: int
    stress: int
    motivation: int
    focus: int
    sleep_quality: int | None = None
    note_preview: str | None = None
    needs_human_support: bool
    safety_metadata: dict | None = None
    created_at: datetime


class WellbeingNoteCreateRequest(BaseModel):
    title: str = "Ghi chú riêng"
    content: str = Field(min_length=1)
    mood_code: str | None = None
    needs_human_support: bool = False
    safety_metadata: dict | None = None


class WellbeingNoteUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    mood_code: str | None = None
    needs_human_support: bool | None = None
    safety_metadata: dict | None = None


class WellbeingNoteOut(BaseModel):
    id: int
    title: str
    content: str
    mood_code: str | None = None
    is_private: bool
    needs_human_support: bool
    safety_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class MusicPlaylistOut(BaseModel):
    id: int
    theme: str
    title: str
    description: str | None = None
    spotify_url: str | None = None
    embed_url: str | None = None
    cover_url: str | None = None
    metadata_json: dict | None = None


class MusicPlaylistRequest(BaseModel):
    theme: str
    title: str
    description: str | None = None
    spotify_url: str | None = None
    embed_url: str | None = None
    cover_url: str | None = None
    is_active: bool = True


class AiReflectOut(BaseModel):
    reflection: str
    suggestions: list[str] = []
