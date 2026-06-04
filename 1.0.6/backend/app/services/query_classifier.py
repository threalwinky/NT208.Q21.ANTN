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
    "co don": 2.2,
    "tui than": 1.8,
    "lac long": 2.0,
    "mat phuong huong": 2.2,
    "khong ai hieu": 2.4,
    "tu ti": 1.8,
    "tram cam": 2.6,
    "tuyet vong": 2.8,
    "so hai": 1.6,
    "khoc": 1.6,
    "ap luc tinh than": 2.4,
    "khong vui": 1.6,
}

ACADEMIC_KEYWORDS = {
    "hoc phi": 2.4,
    "hoc bong": 2.2,
    "tot nghiep": 2.5,
    "ctdt": 2.0,
    "chuong trinh dao tao": 2.5,
    "chuong trinh hoc": 2.2,
    "chuong trinh tai nang": 2.7,
    "tai nang": 2.2,
    "chuong trinh dac biet": 2.5,
    "khung chuong trinh": 2.3,
    "ke hoach hoc tap": 2.2,
    "lo trinh hoc": 2.0,
    "mon hoc": 1.5,
    "mon bat buoc": 2.2,
    "mon tien quyet": 2.2,
    "mon hoc tiep theo": 2.8,
    "hoc tiep mon": 2.8,
    "hoc mon nao tiep": 2.8,
    "nen hoc mon": 2.8,
    "mon minh nen hoc": 3.0,
    "mon nen hoc": 2.6,
    "mon nen dang ky": 2.6,
    "dang ky mon nao": 2.4,
    "dang ky hoc phan nao": 2.6,
    "mon con lai": 2.4,
    "hoc phan con lai": 2.4,
    "chat luong cao": 2.2,
    "tien tien": 1.8,
    "cu nhan": 1.4,
    "ky su": 1.4,
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
    "gpa": 2.4,
    "diem trung binh": 2.4,
    "diem tich luy": 2.2,
    "tin chi": 2.1,
    "tin chi tich luy": 2.5,
    "tien do hoc tap": 2.3,
    "hoc luc": 1.8,
}

LEADERSHIP_KEYWORDS = [
    "hieu truong",
    "pho hieu truong",
    "ban giam hieu",
    "giam hieu",
    "lanh dao truong",
    "hieu pho",
]

UIT_SCHOOL_ALIASES = [
    "uit",
    "dai hoc cong nghe thong tin",
    "dh cong nghe thong tin",
    "dhcntt",
    "truong cong nghe thong tin",
]

OTHER_SCHOOL_ALIASES = [
    "hcmus",
    "hcmut",
    "bach khoa",
    "khoa hoc tu nhien",
    "ueh",
    "uel",
    "ussh",
    "hcmue",
    "huflit",
    "rmit",
    "fpt",
    "ton duc thang",
    "tdtu",
    "van lang",
    "hoa sen",
    "su pham ky thuat",
    "y duoc",
    "can tho",
    "da nang",
    "hust",
    "bach khoa ha noi",
    "dai hoc quoc gia",
    "dhqg",
]

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

# Từ khoá khủng hoảng được lưu Ở DẠNG CÓ DẤU (canonical).
# Lý do: việc bỏ dấu tiếng Việt làm trùng các từ hoàn toàn khác nghĩa và gây
# báo động giả nghiêm trọng, ví dụ:
#   "tự tử" -> "tu tu"        trùng "từ từ" (chậm rãi)
#   "hại bản thân" -> "hai ban than"  trùng "hai bạn thân"
#   "tự vẫn" -> "tu van"      trùng "tư vấn"
# Vì vậy việc dò khủng hoảng phải ưu tiên so khớp trên văn bản CÓ DẤU.
CRISIS_KEYWORDS = {
    "tự tử": 4.0,
    "tự sát": 4.0,
    "tự vẫn": 4.0,
    "không muốn sống": 4.0,
    "không thiết sống": 3.8,
    "muốn chết": 4.0,
    "muốn biến mất": 3.2,
    "kết thúc cuộc đời": 4.0,
    "làm hại bản thân": 4.0,
    "tự làm hại": 4.0,
    "hại bản thân": 3.8,
    "cắt tay": 3.6,
    "uống thuốc tự tử": 4.0,
    "nhảy lầu": 4.0,
    "không còn lý do sống": 4.0,
    "không còn muốn tồn tại": 4.0,
}

# Các cụm khi bỏ dấu sẽ trùng với từ thông dụng (homograph) -> CHỈ được khớp
# ở dạng có dấu, không bao giờ khớp ở dạng đã bỏ dấu.
CRISIS_DIACRITIC_ONLY = {
    "tự tử",          # vs "từ từ"
    "tự vẫn",         # vs "tư vấn"
    "hại bản thân",   # vs "hai bạn thân"
}

CRISIS_TRIGGER_THRESHOLD = 3.6


@dataclass
class QueryAnalysis:
    category: str
    risk_score: float
    is_urgent: bool


def _normalize(text: str) -> str:
    """Chuẩn hoá có BỎ DẤU – dùng cho phân loại chủ đề (academic/announcement...)."""
    normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    compact = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", compact).strip()


def _normalize_keep_diacritics(text: str) -> str:
    """Chuẩn hoá nhưng GIỮ DẤU – dùng riêng cho dò tín hiệu khủng hoảng."""
    lowered = unicodedata.normalize("NFC", (text or "").lower())
    compact = re.sub(r"[^\w]+", " ", lowered, flags=re.UNICODE).replace("_", " ")
    return re.sub(r"\s+", " ", compact).strip()


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """So khớp theo ranh giới từ (tránh khớp chuỗi con như 'tư vấn đời')."""
    if not phrase:
        return False
    return f" {phrase} " in f" {haystack} "


def _mentions_uit_school(normalized: str) -> bool:
    return any(_contains_phrase(normalized, alias) for alias in UIT_SCHOOL_ALIASES)


def _mentions_other_school(normalized: str) -> bool:
    if _mentions_uit_school(normalized):
        return False
    return any(_contains_phrase(normalized, alias) for alias in OTHER_SCHOOL_ALIASES)


def _is_default_uit_leadership_query(normalized: str) -> bool:
    return any(_contains_phrase(normalized, keyword) for keyword in LEADERSHIP_KEYWORDS) and not _mentions_other_school(normalized)


def _score_keywords(normalized: str, keywords: dict[str, float]) -> float:
    score = 0.0
    for phrase, weight in keywords.items():
        # So khớp theo RANH GIỚI TỪ, tránh khớp chuỗi con gây phân loại sai
        # (ví dụ "nan" khớp nhầm bên trong "tài năng" -> quy nhầm WELLBEING).
        if _contains_phrase(normalized, phrase):
            score += weight
    return score


def _crisis_score(content: str) -> float:
    """Tính điểm khủng hoảng theo 2 lớp:

    1) Ưu tiên khớp trên văn bản CÓ DẤU (chính xác, không trùng homograph).
    2) Với các cụm KHÔNG nằm trong danh sách dễ trùng, cho phép khớp thêm ở
       dạng bỏ dấu để bắt được trường hợp người dùng gõ không dấu
       (ví dụ "muon chet", "nhay lau").

    Mỗi từ khoá chỉ được tính điểm một lần (lấy theo lần khớp đầu tiên).
    """
    accented = _normalize_keep_diacritics(content)
    stripped = _normalize(content)
    score = 0.0
    for phrase, weight in CRISIS_KEYWORDS.items():
        matched = _contains_phrase(accented, phrase)
        if not matched and phrase not in CRISIS_DIACRITIC_ONLY:
            matched = _contains_phrase(stripped, _normalize(phrase))
        if matched:
            score += weight
    return score


def analyze_query(content: str) -> QueryAnalysis:
    normalized = _normalize(content)
    if not normalized:
        return QueryAnalysis(category="GENERAL", risk_score=0.0, is_urgent=False)

    if _crisis_score(content) >= CRISIS_TRIGGER_THRESHOLD:
        return QueryAnalysis(category="WELLBEING", risk_score=0.95, is_urgent=True)

    scores = {
        "WELLBEING": _score_keywords(normalized, WELLBEING_KEYWORDS),
        "ANNOUNCEMENT": _score_keywords(normalized, ANNOUNCEMENT_KEYWORDS),
        "ACADEMIC": _score_keywords(normalized, ACADEMIC_KEYWORDS),
        "PLANNING": _score_keywords(normalized, PLANNING_KEYWORDS),
    }
    if _is_default_uit_leadership_query(normalized):
        scores["ACADEMIC"] += 2.8
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
    if any(
        token in normalized
        for token in [
            "nen hoc mon",
            "mon minh nen hoc",
            "hoc tiep mon",
            "hoc mon nao tiep",
            "mon hoc tiep theo",
            "mon nen dang ky",
            "dang ky mon nao",
            "dang ky hoc phan nao",
        ]
    ) and any(token in normalized for token in ["mon", "hoc phan", "chuong trinh", "ctdt", "lo trinh"]):
        scores["ACADEMIC"] += 1.2

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
