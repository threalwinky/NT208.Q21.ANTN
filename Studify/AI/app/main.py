from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


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


def detect_intent(message: str) -> str:
    m = message.lower()
    if any(k in m for k in ["nản", "bỏ cuộc", "stress", "áp lực", "mệt", "burnout", "thất tình"]):
        return "mental_support"
    if any(k in m for k in ["nghề", "career", "thực tập", "cv", "portfolio"]):
        return "career"
    if any(k in m for k in ["lộ trình", "học", "ôn", "môn", "gpa", "điểm"]):
        return "study"
    return "general"


@app.get("/health")
def health():
    return {"ok": True, "service": "ai"}


@app.post("/chat")
def chat(req: ChatRequest):
    intent = detect_intent(req.message)
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
        "reply": response
    }
