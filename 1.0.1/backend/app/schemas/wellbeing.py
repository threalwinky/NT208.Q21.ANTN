from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
