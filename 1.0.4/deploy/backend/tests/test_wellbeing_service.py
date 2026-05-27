from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.users import User, UserRole
from app.models.wellbeing import MoodJournal, MoodState
from app.services.spotify_service import SpotifyTrack
from app.services.wellbeing_service import WellbeingService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_energy_analysis_drops_for_pressure_note() -> None:
    service = WellbeingService()
    mood = MoodState(code="TIRED", display_name="Hơi mệt", intensity=3)

    analysis = service.analyze_energy(mood, "Mình hơi áp lực và deadline dồn nên khá mệt.")

    assert analysis.level <= 2
    assert analysis.label == "Thấp"


def test_energy_analysis_recovers_with_positive_signals() -> None:
    service = WellbeingService()
    mood = MoodState(code="GOOD", display_name="Ổn", intensity=4)

    analysis = service.analyze_energy(mood, "Mọi thứ ổn hơn, mình tập trung lại được và đã xong một phần.")

    assert analysis.level >= 4
    assert analysis.label in {"Ổn", "Tốt"}


def test_build_insight_falls_back_to_stories_without_journals() -> None:
    db = make_session()
    try:
        user = User(username="student", password_hash="x", full_name="Student", email="s@example.com", role=UserRole.STUDENT)
        db.add(user)
        db.commit()
        db.refresh(user)

        insight = __import__("asyncio").run(WellbeingService().build_insight(db, user))

        assert insight["recommendation_mode"] == "story"
        assert insight["recommendations"]
    finally:
        db.close()


def test_build_insight_prefers_music_when_energy_is_low() -> None:
    db = make_session()
    try:
        user = User(username="student2", password_hash="x", full_name="Student 2", email="s2@example.com", role=UserRole.STUDENT)
        mood = MoodState(code="OVERLOADED", display_name="Quá tải", intensity=1)
        db.add_all([user, mood])
        db.flush()
        db.add(MoodJournal(user_id=user.id, mood_state_id=mood.id, short_note="Mình quá tải và hơi đuối vì deadline dồn.", energy_level=1))
        db.commit()

        service = WellbeingService()

        async def fake_music(theme: str = "focus", limit: int = 3):
            return [
                SpotifyTrack(
                    track_id="test-track",
                    title="Study Night",
                    artist="Lo-fi Lab",
                    album="Late Session",
                    url="https://open.spotify.com/track/test-track",
                    embed_url="https://open.spotify.com/embed/track/test-track",
                )
            ][:limit]

        service.music_tracks = fake_music  # type: ignore[method-assign]
        insight = __import__("asyncio").run(service.build_insight(db, user))

        assert insight["recommendation_mode"] == "music"
        assert insight["latest_energy_level"] <= 2
        assert insight["music_tracks"]
    finally:
        db.close()


def test_spotify_fallback_tracks_use_embed_urls() -> None:
    service = WellbeingService()

    tracks = service.spotify._fallback_tracks("upbeat", 3)

    assert len(tracks) == 3
    assert all(track.track_id for track in tracks)
    assert all(track.embed_url.startswith("https://open.spotify.com/embed/track/") for track in tracks)


def test_build_preview_insight_uses_selected_mood() -> None:
    db = make_session()
    try:
        user = User(username="student3", password_hash="x", full_name="Student 3", email="s3@example.com", role=UserRole.STUDENT)
        mood = MoodState(code="GOOD", display_name="Ổn", intensity=4)
        db.add_all([user, mood])
        db.commit()
        db.refresh(user)
        db.refresh(mood)

        service = WellbeingService()

        async def fake_music(theme: str = "focus", limit: int = 6):
            return [
                SpotifyTrack(
                    track_id="upbeat-track",
                    title="Bright Day",
                    artist="Campus Mix",
                    album="Mood Shift",
                    url="https://open.spotify.com/track/upbeat-track",
                    embed_url="https://open.spotify.com/embed/track/upbeat-track",
                )
            ][:limit]

        service.music_tracks = fake_music  # type: ignore[method-assign]
        insight = __import__("asyncio").run(service.build_preview_insight(db, user, mood.id, "Hôm nay mình khá ổn và có tiến triển."))

        assert insight["latest_mood_label"] == "Ổn"
        assert insight["music_theme"] == "upbeat"
        assert insight["music_tracks"]
    finally:
        db.close()
