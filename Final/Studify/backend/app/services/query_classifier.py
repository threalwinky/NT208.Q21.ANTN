from __future__ import annotations

from dataclasses import dataclass


MOOD_KEYWORDS = [
    "stress",
    "áp lực",
    "mệt mỏi",
    "buồn",
    "nản",
    "quá tải",
    "chán",
    "lo âu",
    "không ổn",
    "mất động lực",
    "deadline dồn",
    "đuối",
    "kiệt sức",
    "muốn tâm sự",
    "cần tâm sự",
    "rối quá",
]

ACADEMIC_KEYWORDS = [
    "học phí",
    "học bổng",
    "tốt nghiệp",
    "ctđt",
    "chương trình đào tạo",
    "đăng ký học phần",
    "lịch thi",
    "lịch học",
    "giấy xác nhận",
    "daa",
    "ctsv",
    "courses",
    "oep",
]

ANNOUNCEMENT_KEYWORDS = ["thông báo", "tin mới", "cập nhật", "sự kiện", "hạn chót"]


@dataclass
class QueryAnalysis:
    category: str
    risk_score: float
    is_urgent: bool


def analyze_query(content: str) -> QueryAnalysis:
    normalized = (content or "").lower()
    if any(keyword in normalized for keyword in MOOD_KEYWORDS):
        return QueryAnalysis(category="WELLBEING", risk_score=0.12, is_urgent=False)

    if any(keyword in normalized for keyword in ANNOUNCEMENT_KEYWORDS):
        return QueryAnalysis(category="ANNOUNCEMENT", risk_score=0.0, is_urgent=False)

    if any(keyword in normalized for keyword in ACADEMIC_KEYWORDS):
        return QueryAnalysis(category="ACADEMIC", risk_score=0.0, is_urgent=False)

    return QueryAnalysis(category="GENERAL", risk_score=0.0, is_urgent=False)
