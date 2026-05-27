from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from sqlalchemy.orm import Session

from app.models.users import User
from app.models.wellbeing import MoodJournal, MoodState, SystemConfig
from app.services.spotify_service import SpotifyService, SpotifyTrack


@dataclass
class EnergyAnalysis:
    level: int
    label: str
    summary: str
    signals: list[str]


@dataclass
class WellbeingRecommendation:
    kind: str
    title: str
    subtitle: str
    description: str
    url: str | None = None
    image_url: str | None = None


class WellbeingService:
    def __init__(self) -> None:
        self.spotify = SpotifyService()
        self.love_keywords = {"yêu", "thích", "crush", "hẹn hò", "tình yêu", "thương", "romance"}
        self.music_theme_labels = {
            "calm": "Chill / lo-fi",
            "focus": "Tập trung nhẹ",
            "upbeat": "EDM / vui vẻ",
            "love": "Tình yêu / dễ chịu",
        }
        self.low_keywords = {
            "mệt": (-0.7, "mệt"),
            "đuối": (-0.8, "đuối"),
            "áp lực": (-1.0, "áp lực"),
            "quá tải": (-1.1, "quá tải"),
            "dồn": (-0.5, "deadline dồn"),
            "rối": (-0.6, "rối"),
            "khó tập trung": (-0.7, "khó tập trung"),
            "thiếu ngủ": (-0.9, "thiếu ngủ"),
            "chậm": (-0.4, "chậm nhịp"),
        }
        self.high_keywords = {
            "ổn": (0.4, "ổn hơn"),
            "đỡ": (0.5, "đỡ hơn"),
            "xong": (0.5, "đã xử lý được một phần"),
            "tiến triển": (0.7, "có tiến triển"),
            "tập trung": (0.5, "tập trung"),
            "nhẹ đầu": (0.7, "nhẹ đầu"),
            "thoải mái": (0.8, "thoải mái"),
            "vui": (0.7, "vui hơn"),
        }

    def _clamp(self, value: float, minimum: float = 1.0, maximum: float = 5.0) -> float:
        return max(minimum, min(maximum, value))

    def _energy_label(self, level: int) -> str:
        if level <= 2:
            return "Thấp"
        if level == 3:
            return "Trung bình"
        if level == 4:
            return "Ổn"
        return "Tốt"

    def _trend_label(self, current_average: float, previous_average: float | None) -> str:
        if previous_average is None:
            return "STABLE"
        delta = current_average - previous_average
        if delta <= -0.35:
            return "DOWN"
        if delta >= 0.35:
            return "UP"
        return "STABLE"

    def low_energy_threshold(self, db: Session) -> float:
        config = db.query(SystemConfig).filter(SystemConfig.key == "energy_support_threshold").first()
        if config:
            return float(config.value_json.get("low_threshold", 2.4))
        return 2.4

    def analyze_energy(self, mood_state: MoodState | None, note: str | None) -> EnergyAnalysis:
        score = float(mood_state.intensity if mood_state else 3)
        normalized_note = (note or "").lower().strip()
        signals: list[str] = []

        for phrase, (delta, label) in self.low_keywords.items():
            if phrase in normalized_note:
                score += delta
                signals.append(label)
        for phrase, (delta, label) in self.high_keywords.items():
            if phrase in normalized_note:
                score += delta
                signals.append(label)

        if mood_state and mood_state.display_name:
            signals.insert(0, mood_state.display_name.lower())

        level = int(round(self._clamp(score)))
        label = self._energy_label(level)

        if level <= 2:
            summary = "Năng lượng đang thấp. Hợp hơn với việc ngắn, nhịp chậm và một khoảng nghỉ thật sự."
        elif level == 3:
            summary = "Năng lượng đang ở mức vừa. Nên giữ một việc chính, phần còn lại chia nhỏ để đỡ ngợp."
        elif level == 4:
            summary = "Nhịp hiện tại khá ổn. Bạn có thể xử lý một block sâu rồi chuyển sang các việc ngắn."
        else:
            summary = "Năng lượng đang tốt. Đây là lúc phù hợp để chốt một việc quan trọng trước."

        compact_signals = []
        for item in signals:
            if item not in compact_signals:
                compact_signals.append(item)
        return EnergyAnalysis(level=level, label=label, summary=summary, signals=compact_signals[:4])

    def motivational_stories(self, limit: int = 3) -> list[WellbeingRecommendation]:
        stories = [
            WellbeingRecommendation(
                kind="story",
                title="Bắt đầu lại từ 10 phút",
                subtitle="Nhắc nhẹ",
                description="Có những ngày không cần thắng lớn. Chỉ cần mở việc khó nhất ra 10 phút, bạn đã kéo mình trở lại đường ray.",
            ),
            WellbeingRecommendation(
                kind="story",
                title="Một deadline trễ không định nghĩa cả học kỳ",
                subtitle="Giữ nhịp",
                description="Nhiều bạn đuối vì gom mọi lỗi thành một kết luận quá nặng. Tách từng việc ra, sửa từng chỗ nhỏ, nhịp học sẽ dễ thở hơn nhiều.",
            ),
            WellbeingRecommendation(
                kind="story",
                title="Khoảng nghỉ đúng lúc cũng là tiến độ",
                subtitle="Phục hồi",
                description="Một cốc nước, 15 phút rời màn hình và vài hơi thở sâu đôi khi giúp bạn làm nhanh hơn cả một giờ cố gồng.",
            ),
        ]
        return stories[:limit]

    def steady_rhythm_tips(self, limit: int = 3) -> list[WellbeingRecommendation]:
        tips = [
            WellbeingRecommendation(
                kind="tip",
                title="Chốt 1 việc chính trước",
                subtitle="Nhịp học",
                description="Đặt một block 45-60 phút cho việc quan trọng nhất rồi mới mở các việc lặt vặt.",
            ),
            WellbeingRecommendation(
                kind="tip",
                title="Giữ một khoảng trống giữa các block",
                subtitle="Phục hồi",
                description="Đừng dồn lịch kín hoàn toàn. Một khoảng trống 10-15 phút giúp đầu óc không bị bào mòn quá nhanh.",
            ),
            WellbeingRecommendation(
                kind="tip",
                title="Ghi ngắn điều đang kẹt",
                subtitle="Làm rõ",
                description="Nếu thấy khó bắt đầu, hãy viết đúng một dòng: mình đang kẹt ở bước nào.",
            ),
        ]
        return tips[:limit]

    def choose_music_theme(self, mood_state: MoodState | None, analysis: EnergyAnalysis, note: str | None) -> str:
        normalized_note = (note or "").lower().strip()
        mood_label = (mood_state.display_name.lower().strip() if mood_state and mood_state.display_name else "")

        if any(keyword in normalized_note for keyword in self.love_keywords):
            return "love"
        if analysis.level <= 2 or mood_label in {"quá tải", "áp lực"}:
            return "calm"
        if analysis.level >= 4 or mood_label in {"rất ổn", "ổn"}:
            return "upbeat"
        return "focus"

    async def music_tracks(self, theme: str = "focus", limit: int = 6) -> list[SpotifyTrack]:
        return await self.spotify.search_tracks(theme=theme, limit=limit)

    def serialize_journal(self, journal: MoodJournal) -> tuple[int, str, str, list[str]]:
        analysis = self.analyze_energy(journal.mood_state, journal.short_note)
        return analysis.level, analysis.label, analysis.summary, analysis.signals

    def _recent_analyses(self, db: Session, user: User, limit: int = 8) -> list[EnergyAnalysis]:
        journals = (
            db.query(MoodJournal)
            .filter(MoodJournal.user_id == user.id, MoodJournal.is_soft_deleted.is_(False))
            .order_by(MoodJournal.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self.analyze_energy(item.mood_state, item.short_note) for item in journals]

    async def _build_insight_payload(
        self,
        db: Session,
        latest_analysis: EnergyAnalysis,
        latest_mood_state: MoodState | None,
        note: str | None,
        levels: list[int],
    ) -> dict:
        threshold = self.low_energy_threshold(db)
        current_average = mean(levels[:3]) if levels else float(latest_analysis.level)
        previous_average = mean(levels[3:6]) if len(levels) >= 6 else None
        music_theme = self.choose_music_theme(latest_mood_state, latest_analysis, note)
        music_tracks = await self.music_tracks(theme=music_theme, limit=6)

        if latest_analysis.level <= threshold or current_average <= threshold:
            recommendations = self.motivational_stories(limit=3)
            recommendation_mode = "music"
        elif latest_analysis.level <= 3:
            recommendations = self.motivational_stories(limit=3)
            recommendation_mode = "story"
        else:
            recommendations = self.steady_rhythm_tips(limit=3)
            recommendation_mode = "tip"

        return {
            "latest_energy_level": latest_analysis.level,
            "latest_energy_label": latest_analysis.label,
            "latest_mood_label": latest_mood_state.display_name if latest_mood_state else None,
            "average_energy_level": round(mean(levels), 1) if levels else float(latest_analysis.level),
            "trend": self._trend_label(current_average, previous_average),
            "summary": latest_analysis.summary,
            "signals": latest_analysis.signals,
            "low_energy_threshold": threshold,
            "recommendation_mode": recommendation_mode,
            "recommendations": recommendations,
            "music_theme": music_theme,
            "music_theme_label": self.music_theme_labels[music_theme],
            "music_tracks": music_tracks,
            "energy_series": list(reversed(levels[:7])),
        }

    async def build_preview_insight(
        self,
        db: Session,
        user: User,
        mood_state_id: int | None = None,
        short_note: str | None = None,
    ) -> dict:
        mood_state = db.query(MoodState).filter(MoodState.id == mood_state_id).first() if mood_state_id else None
        latest_analysis = self.analyze_energy(mood_state, short_note)
        historical_analyses = self._recent_analyses(db, user, limit=7)
        levels = [latest_analysis.level, *[item.level for item in historical_analyses]]
        return await self._build_insight_payload(
            db,
            latest_analysis=latest_analysis,
            latest_mood_state=mood_state,
            note=short_note,
            levels=levels,
        )

    async def build_insight(self, db: Session, user: User) -> dict:
        journals = (
            db.query(MoodJournal)
            .filter(MoodJournal.user_id == user.id, MoodJournal.is_soft_deleted.is_(False))
            .order_by(MoodJournal.created_at.desc())
            .limit(8)
            .all()
        )

        if not journals:
            recommendations = self.motivational_stories(limit=3)
            music_theme = "focus"
            music_tracks = await self.music_tracks(theme=music_theme, limit=6)
            return {
                "latest_energy_level": 3,
                "latest_energy_label": "Trung bình",
                "latest_mood_label": None,
                "average_energy_level": 3.0,
                "trend": "STABLE",
                "summary": "Chưa có đủ dữ liệu nhật ký. Bạn có thể lưu một dòng ngắn để Studify bắt đầu đọc nhịp của bạn.",
                "signals": [],
                "low_energy_threshold": self.low_energy_threshold(db),
                "recommendation_mode": "story",
                "recommendations": recommendations,
                "music_theme": music_theme,
                "music_theme_label": self.music_theme_labels[music_theme],
                "music_tracks": music_tracks,
                "energy_series": [],
            }

        analyses = [self.analyze_energy(item.mood_state, item.short_note) for item in journals]
        levels = [item.level for item in analyses]
        latest = analyses[0]
        return await self._build_insight_payload(
            db,
            latest_analysis=latest,
            latest_mood_state=journals[0].mood_state,
            note=journals[0].short_note,
            levels=levels,
        )
