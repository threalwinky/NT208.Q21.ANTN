from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


WELLBEING_KEYWORDS = {
    "stress": 2.2,
    "ap luc": 2.2,
    "met moi": 1.8,
    "buon": 1.8,
    "nan": 1.6,
    "qua tai": 2.3,
    "chan": 1.4,
    "lo au": 1.8,
    "khong on": 2.1,
    "mat dong luc": 2.3,
    "deadline don": 2.2,
    "duoi": 1.7,
    "kiet suc": 2.4,
    "muon tam su": 2.4,
    "can tam su": 2.4,
    "roi qua": 1.8,
    "hoi met": 1.4,
}

ACADEMIC_KEYWORDS = {
    "hoc phi": 2.4,
    "hoc bong": 2.2,
    "tot nghiep": 2.5,
    "ctdt": 2.0,
    "chuong trinh dao tao": 2.5,
    "dang ky hoc phan": 2.6,
    "lich thi": 2.6,
    "lich hoc": 2.2,
    "lich nghi": 1.7,
    "nghi he": 2.0,
    "ve he": 1.7,
    "ke hoach nam": 2.4,
    "ke hoach dao tao nam hoc": 2.8,
    "giay xac nhan": 2.4,
    "giay gioi thieu": 2.1,
    "bao luu": 2.2,
    "tam ngung": 2.0,
    "thoi hoc": 2.0,
    "canh bao hoc vu": 2.7,
    "canh bao hoc tap": 2.7,
    "xu ly hoc vu": 2.4,
    "daa": 1.6,
    "ctsv": 1.3,
    "khtc": 1.6,
    "courses": 1.3,
    "oep": 1.4,
    "hoc vu": 2.3,
    "thu tuc": 2.2,
    "quy che": 2.0,
    "quy dinh": 1.8,
    "tieng anh": 2.4,
    "ngoai ngu": 2.4,
    "chuan dau ra": 2.8,
    "chuan qua trinh": 2.1,
    "dau ra": 1.7,
    "chung chi tieng anh": 3.0,
    "chung chi ngoai ngu": 2.8,
    "toeic": 2.4,
    "ielts": 2.4,
    "toefl": 2.2,
    "vstep": 2.2,
    "vnu ept": 2.5,
    "anh van": 2.1,
}

ANNOUNCEMENT_KEYWORDS = {
    "thong bao": 2.8,
    "tin moi": 2.2,
    "cap nhat": 1.8,
    "su kien": 1.8,
    "han chot": 2.1,
    "moi nhat": 2.0,
    "tuan nay co gi": 2.0,
    "dau vao": 0.8,
}

PLANNING_KEYWORDS = {
    "sap lai": 2.9,
    "len ke hoach": 2.8,
    "ke hoach": 2.0,
    "tuan nay": 1.8,
    "nhac viec": 2.5,
    "deadline": 1.8,
    "viec can lam": 2.6,
    "to do": 2.1,
    "planner": 2.0,
    "phan bo": 2.4,
    "sap xep": 2.1,
    "lich cua minh": 2.0,
    "giup minh chia": 2.6,
}

URGENT_KEYWORDS = {
    "gap": 1.3,
    "ngay hom nay": 1.1,
    "hom nay": 0.7,
    "ngay mai": 0.7,
    "sap tre": 1.1,
    "sat han": 1.2,
    "can ngay": 1.0,
    "qua han": 1.3,
    "kip khong": 0.8,
}

CRISIS_KEYWORDS = {
    "tu tu": 4.0,
    "tu sat": 4.0,
    "tu van doi": 4.0,
    "khong muon song": 4.0,
    "khong thiet song": 3.8,
    "muon chet": 4.0,
    "muon bien mat": 3.2,
    "ket thuc cuoc doi": 4.0,
    "lam hai ban than": 4.0,
    "tu lam hai": 4.0,
    "hai ban than": 3.8,
    "cat tay": 3.6,
    "uong thuoc tu tu": 4.0,
    "nhay lau": 4.0,
    "khong con ly do song": 4.0,
    "khong con muon ton tai": 4.0,
}


@dataclass
class QueryAnalysis:
    category: str
    risk_score: float
    is_urgent: bool


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    compact = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", compact).strip()


def _score_keywords(normalized: str, keywords: dict[str, float]) -> float:
    score = 0.0
    for phrase, weight in keywords.items():
        if phrase in normalized:
            score += weight
    return score


def analyze_query(content: str) -> QueryAnalysis:
    normalized = _normalize(content)
    if not normalized:
        return QueryAnalysis(category="GENERAL", risk_score=0.0, is_urgent=False)

    crisis_score = _score_keywords(normalized, CRISIS_KEYWORDS)
    if crisis_score >= 3.6:
        return QueryAnalysis(category="WELLBEING", risk_score=0.95, is_urgent=True)

    scores = {
        "WELLBEING": _score_keywords(normalized, WELLBEING_KEYWORDS),
        "ANNOUNCEMENT": _score_keywords(normalized, ANNOUNCEMENT_KEYWORDS),
        "ACADEMIC": _score_keywords(normalized, ACADEMIC_KEYWORDS),
        "PLANNING": _score_keywords(normalized, PLANNING_KEYWORDS),
    }
    urgency_score = _score_keywords(normalized, URGENT_KEYWORDS)

    if "?" in content and scores["ACADEMIC"] > 0:
        scores["ACADEMIC"] += 0.3
    if any(token in normalized for token in ["giup minh", "tu van", "goi y"]) and scores["PLANNING"] > 0:
        scores["PLANNING"] += 0.5
    if any(token in normalized for token in ["moi nhat", "hom nay", "tuan nay"]) and scores["ANNOUNCEMENT"] > 0:
        scores["ANNOUNCEMENT"] += 0.4
    if "thong bao" in normalized:
        scores["ANNOUNCEMENT"] += 1.3
    if any(token in normalized for token in ["cap nhat moi", "moi khong", "moi nhat", "co cap nhat"]) and any(token in normalized for token in ["lich thi", "lich hoc", "dau vao", "anh van", "tieng anh"]):
        scores["ANNOUNCEMENT"] += 1.2
    if any(token in normalized for token in ["nghi he", "lich nghi", "ke hoach nam", "ke hoach dao tao nam hoc"]) and scores["ACADEMIC"] > 0:
        scores["ACADEMIC"] += 0.6
    if "cap nhat" in normalized and (scores["ACADEMIC"] > 0 or scores["ANNOUNCEMENT"] > 0):
        scores["ANNOUNCEMENT"] += 0.9
    if any(token in normalized for token in ["co gi moi", "moi khong", "moi nao"]) and scores["ACADEMIC"] > 0:
        scores["ANNOUNCEMENT"] += 0.8
    if any(token in normalized for token in ["tieng anh", "ngoai ngu", "chuan dau ra", "vnu ept", "toeic", "ielts"]):
        scores["ACADEMIC"] += 0.9
    if any(token in normalized for token in ["dang ky hoc phan", "dang ky hoc", "hoc phi", "chuong trinh dao tao", "ctdt", "oep", "khtc", "canh bao hoc vu"]) and scores["ACADEMIC"] > 0:
        scores["ACADEMIC"] += 0.8

    category, top_score = max(scores.items(), key=lambda item: item[1])
    if top_score < 1.2:
        category = "GENERAL"

    if category == "PLANNING" and scores["WELLBEING"] >= scores["PLANNING"] + 0.8:
        category = "WELLBEING"
    if category == "ANNOUNCEMENT" and scores["ACADEMIC"] >= scores["ANNOUNCEMENT"] - 0.2 and any(token in normalized for token in ["dang ky hoc phan", "dang ky hoc", "hoc phi", "ctdt", "oep", "khtc", "thu tuc", "quy che", "quy dinh", "nghi he", "ke hoach nam"]):
        category = "ACADEMIC"
    if category == "ACADEMIC" and any(token in normalized for token in ["lich thi", "lich hoc"]) and any(token in normalized for token in ["cap nhat", "moi khong", "moi nhat", "dau vao"]):
        category = "ANNOUNCEMENT"
    if category == "ACADEMIC" and scores["ANNOUNCEMENT"] >= scores["ACADEMIC"] + 0.8:
        category = "ANNOUNCEMENT"

    risk_score = 0.0
    if category == "WELLBEING":
        risk_score = min(0.42, 0.1 + (scores["WELLBEING"] * 0.04))
    elif category == "PLANNING" and scores["WELLBEING"] > 0:
        risk_score = 0.08

    is_urgent = urgency_score >= 1.2 or ("deadline" in normalized and any(token in normalized for token in ["hom nay", "ngay mai"]))
    return QueryAnalysis(category=category, risk_score=round(risk_score, 2), is_urgent=is_urgent)
