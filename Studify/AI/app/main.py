from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Tuple
import re
import unicodedata

import joblib

app = FastAPI()

MODEL_PATH = Path("data/intent_model.joblib")
INTENT_PIPELINE = None
MIN_CONFIDENCE = 0.45


class Profile(BaseModel):
    name: str = ""
    major: str = ""
    year: str = ""
    careerGoal: str = ""
    studyHabits: str = ""
    gpaTarget: str = ""


class ChatRequest(BaseModel):
    message: str
    profile: Profile


MOTIVATION_STORIES = [
    "Có nhiều người từng trượt đại học vài lần nhưng vẫn kiên trì học kỹ năng thực tế, rồi trở thành kỹ sư giỏi nhờ đi từng bước nhỏ mỗi ngày.",
    "Nhiều bạn từng mất động lực vì điểm thấp, nhưng khi đổi sang học Active Recall + Pomodoro, chỉ sau 3 tháng đã tăng rõ rệt hiệu suất.",
    "Có người từng bị từ chối thực tập liên tục, nhưng sau khi xây lại portfolio dự án cá nhân, họ đã nhận offer đúng ngành mong muốn."
]


def load_model() -> None:
    global INTENT_PIPELINE, MIN_CONFIDENCE
    if not MODEL_PATH.exists():
        return

    artifact = joblib.load(MODEL_PATH)
    INTENT_PIPELINE = artifact.get("pipeline")
    MIN_CONFIDENCE = float(artifact.get("min_confidence", MIN_CONFIDENCE))


def detect_intent_ml(message: str) -> Tuple[Optional[str], float]:
    if INTENT_PIPELINE is None:
        return None, 0.0

    probabilities = INTENT_PIPELINE.predict_proba([message])[0]
    classes = INTENT_PIPELINE.classes_
    best_idx = int(probabilities.argmax())
    best_label = str(classes[best_idx])
    best_confidence = float(probabilities[best_idx])

    if best_confidence >= MIN_CONFIDENCE:
        return best_label, best_confidence
    return None, best_confidence


def detect_intent(message: str) -> str:
    def normalize_text(text: str) -> str:
        value = text.lower().replace("đ", "d")
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    normalized = normalize_text(message)
    tokens = set(normalized.split())

    keyword_groups = {
        "mental_support": {
            "single": {
                "stress", "apluc", "met", "buon", "chan", "nan", "burnout", "coidon",
                "loau", "matngu", "kiet", "hoangmang", "tuyetvong", "suy", "tramcam",
                "thattinh", "khoc", "be tac"
            },
            "phrases": {
                "bo cuoc", "mat dong luc", "ap luc", "qua met", "khong on",
                "khong the tiep tuc", "khong biet lam sao", "muon nghi hoc", "het dong luc"
            },
        },
        "career": {
            "single": {
                "career", "nghe", "intern", "thuctap", "cv", "portfolio", "phongvan",
                "fresher", "linkedin", "vieclam", "offer", "congty", "itjob", "resum"
            },
            "phrases": {
                "dinh huong nghe nghiep", "tim viec", "xin viec", "thuc tap",
                "viet cv", "xay portfolio", "roi mon di lam", "chon huong nghe"
            },
        },
        "study": {
            "single": {
                "hoc", "on", "mon", "gpa", "diem", "deadline", "lich", "tinchi",
                "dangky", "decuong", "kiemtra", "thicuoiky", "doan", "baitap", "pomodoro",
                "active", "recall", "uutien", "kehoach", "toiuu", "study", "hocky",
                "hocvu", "uit", "ctdt"
            },
            "phrases": {
                "lo trinh hoc", "dang ky mon", "cai thien gpa", "ke hoach hoc",
                "phan bo thoi gian", "on thi", "sap xep lich hoc", "hoc phan",
                "co van hoc tap", "quy che hoc vu", "hoc lai", "hoc cai thien"
            },
        },
    }

    scores = {"mental_support": 0, "career": 0, "study": 0}

    joined_text = f" {normalized} "
    for intent, group in keyword_groups.items():
        for word in group["single"]:
            if word in tokens:
                scores[intent] += 1
        for phrase in group["phrases"]:
            phrase_norm = f" {phrase} "
            if phrase_norm in joined_text:
                scores[intent] += 2

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score <= 0:
        return "general"

    if scores["mental_support"] >= 2 and scores["mental_support"] >= scores["study"]:
        return "mental_support"

    return best_intent


load_model()


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ai",
        "model_loaded": INTENT_PIPELINE is not None,
        "model_path": str(MODEL_PATH)
    }


@app.post("/chat")
def chat(req: ChatRequest):
    predicted_intent, confidence = detect_intent_ml(req.message)
    intent = predicted_intent or detect_intent(req.message)
    name = req.profile.name or "bạn"
    major = req.profile.major or "ngành của bạn"

    if intent == "mental_support":
        response = (
            f"Mình hiểu cảm giác của {name} lúc này. Hít thở sâu 4-7-8 trong 2 phút nhé. "
            f"Một câu chuyện thật để bạn có thêm động lực: {MOTIVATION_STORIES[1]} "
            "Nếu cảm xúc kéo dài nhiều ngày và ảnh hưởng mạnh, bạn nên tìm đến chuyên gia tâm lý hoặc cố vấn sinh viên."
        )
    elif intent == "career":
        response = (
            f"Với nền tảng {major}, mình gợi ý 2 hướng gần nhất: (1) vị trí thực tập đúng chuyên môn, "
            "(2) vai trò liên quan kỹ năng số. Tuần này hãy làm 1 mini-project + cập nhật CV + nộp 5 vị trí phù hợp."
        )
    elif intent == "study":
        response = (
            f"{name} có thể áp dụng khung 6 tuần: 5 buổi/tuần, mỗi buổi 2 block Pomodoro 50/10. "
            "Mỗi cuối tuần: tự kiểm tra bằng 20 câu hỏi Active Recall và điều chỉnh phần còn yếu."
        )
    else:
        response = (
            f"Mình là Studify. Mình có thể hỗ trợ {name} về học tập, định hướng nghề, "
            "lên lịch học và động lực tinh thần. Bạn muốn bắt đầu từ mục nào?"
        )

    return {
        "intent": intent,
        "reply": response,
        "confidence": confidence if predicted_intent else None,
        "source": "ml" if predicted_intent else "rule"
    }

