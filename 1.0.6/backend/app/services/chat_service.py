from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.advisor import CourseRecordStatus
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import StructuredKnowledgeFact
from app.models.users import User
from app.models.wellbeing import SystemConfig
from app.schemas.chat import ChatReply, CitationItem
from app.services.citation_validator import CitationValidator
from app.services.llm import get_llm_provider
from app.services.llm.mimo_provider import TOOL_STATUS_PREFIX
from app.services.query_classifier import QueryAnalysis, analyze_query
from app.services.query_rewriter import LEADERSHIP_KEYWORDS, OTHER_SCHOOL_ALIASES, QueryRewriter, UIT_SCHOOL_ALIASES
from app.services.rag_service import RagService, RetrievedContext

logger = logging.getLogger(__name__)
from app.services.structured_facts_service import StructuredFactsService


VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass
class PreparedTurn:
    analysis: QueryAnalysis
    effective_query: str
    contexts: list[RetrievedContext]
    facts: list[StructuredKnowledgeFact]
    citations: list[CitationItem]
    suggestions: list[str]
    messages: list[dict[str, str]]


@dataclass
class SearchPlan:
    needs_web_search: bool
    queries: list[str]
    reason: str = ""


class ChatService:
    def __init__(self) -> None:
        self.llm = get_llm_provider()
        self.rag = RagService()
        self.facts = StructuredFactsService()
        self.query_rewriter = QueryRewriter()
        self.citation_validator = CitationValidator()

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        compact = re.sub(r"[^a-z0-9]+", " ", stripped)
        return re.sub(r"\s+", " ", compact).strip()

    def _has_any(self, haystack: str, needles: list[str]) -> bool:
        return any(needle in haystack for needle in needles)

    def _contains_phrase(self, normalized: str, phrase: str) -> bool:
        return bool(re.search(rf"\b{re.escape(phrase)}\b", normalized))

    def _mentions_uit_school(self, normalized: str) -> bool:
        return any(self._contains_phrase(normalized, alias) for alias in UIT_SCHOOL_ALIASES)

    def _mentions_other_school(self, normalized: str) -> bool:
        if self._mentions_uit_school(normalized):
            return False
        return any(self._contains_phrase(normalized, alias) for alias in OTHER_SCHOOL_ALIASES)

    def _is_default_uit_school_context_query(self, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if not normalized:
            return False
        return any(self._contains_phrase(normalized, keyword) for keyword in LEADERSHIP_KEYWORDS) and not self._mentions_other_school(normalized)

    def _route_analysis(self, raw_effective_query: str, effective_query: str, analysis: QueryAnalysis) -> QueryAnalysis:
        if analysis.category == "GENERAL" and self._is_default_uit_school_context_query(effective_query):
            return QueryAnalysis(category="ACADEMIC", risk_score=analysis.risk_score, is_urgent=analysis.is_urgent)
        return analysis

    def _fact_type_value(self, value: str | object) -> str:
        return value.value if hasattr(value, "value") else str(value)

    def _query_topics(self, text: str) -> set[str]:
        normalized = self._normalize(text)
        topics: set[str] = set()

        if self._has_any(
            normalized,
            [
                "tieng anh",
                "ngoai ngu",
                "chuan dau ra",
                "chuan qua trinh",
                "toeic",
                "ielts",
                "toefl",
                "vstep",
                "vnu ept",
                "chung chi",
            ],
        ):
            topics.add("english")
        if self._has_any(normalized, ["dang ky hoc phan", "dang ky hoc", "dkhp", "xac nhan dkhp", "hoc phan"]):
            topics.add("registration")
        if self._has_any(normalized, ["hoc phi", "thu hoc phi", "dong hoc phi", "mien giam hoc phi", "gia han hoc phi"]):
            topics.add("tuition")
        if self._has_any(normalized, ["hoc bong", "khuyen khich hoc tap", "kkht", "ngoai ngan sach", "xet hoc bong"]):
            topics.add("scholarship")
        if self._has_any(normalized, ["tot nghiep", "xet tot nghiep", "dieu kien tot nghiep", "ra truong", "khoa luan", "do an"]):
            topics.add("graduation")
        if self._has_any(normalized, ["giay xac nhan", "xac nhan sinh vien", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc", "chuyen nganh", "song nganh", "cong nhan tin chi"]):
            topics.add("procedure")
        if self._has_any(normalized, ["lich thi", "lich hoc", "thoi khoa bieu", "tkb", "giua ky", "cuoi ky", "lich dkhp", "dkhp"]):
            topics.add("schedule")
        if self._has_any(normalized, ["ke hoach nam", "ke hoach dao tao nam hoc", "lich nghi", "nghi he", "ve he", "hoc ky he", "hk he", "khai giang", "tet am lich"]):
            topics.add("annual_plan")
        if self._has_any(normalized, ["canh bao hoc vu", "canh bao hoc tap", "canh bao sinh vien", "xu ly hoc vu", "ket qua dang ky hoc phan", "ket qua hoc tap"]):
            topics.add("academic_warning")
        if self._has_any(
            normalized,
            [
                "ctdt",
                "chuong trinh dao tao",
                "chuong trinh hoc",
                "ke hoach hoc tap",
                "khung chuong trinh",
                "lo trinh hoc",
                "hoc mon nao",
                "hoc mon nao tiep",
                "hoc tiep mon",
                "mon hoc tiep theo",
                "nen hoc mon",
                "nganh hoc",
            ],
        ):
            topics.add("curriculum")
        if self._has_any(
            normalized,
            [
                "cua minh",
                "cua toi",
                "minh con bao nhieu tin",
                "con bao nhieu tin",
                "bao nhieu tin nua",
                "gpa minh",
                "gpa cua minh",
                "diem trung binh cua minh",
                "tin chi minh",
                "tin chi cua minh",
                "tien do tot nghiep",
                "toi con thieu",
                "minh con thieu",
                "minh can them",
                "minh dang hoc chuong trinh gi",
                "hoc them mon gi",
                "can hoc them mon",
                "mon minh nen hoc",
                "minh nen hoc mon",
                "toi nen hoc mon",
                "nen hoc mon gi",
                "nen hoc mon nao",
                "hoc mon nao tiep",
                "hoc tiep mon nao",
                "hoc tiep mon gi",
                "mon hoc tiep theo",
                "mon nen dang ky",
                "dang ky mon nao",
                "dang ky hoc phan nao",
                "theo chuong trinh hoc",
                "theo chuong trinh dao tao",
                "theo ctdt",
                "lo trinh hoc cua minh",
                "ke hoach hoc tap cua minh",
            ],
        ):
            topics.add("personal_academic")
        if self._has_any(normalized, ["hieu truong", "pho hieu truong", "ban giam hieu", "giam hieu", "lanh dao truong", "hieu pho", "pho hieu truong phu trach", "nguyen tan tran minh khang", "nguyen luu thuy ngan"]):
            topics.add("leadership")
        if self._has_any(normalized, ["oep", "tai nang", "chat luong cao", "tien tien", "cttn", "ctclc", "cttt", "bcu", "uon"]):
            topics.add("special_program")
        return topics

    def _looks_follow_up(self, content: str) -> bool:
        normalized = self._normalize(content)
        if not normalized:
            return False

        tokens = normalized.split()
        follow_up_phrases = {
            "la bao nhieu",
            "bao nhieu",
            "la sao",
            "the nao",
            "cu the",
            "chi tiet hon",
            "con ielts",
            "con toeic",
            "con vstep",
            "con vnu ept",
            "con dau ra",
            "co chac khong",
            "nghia la sao",
            "ro hon",
            "vay con",
            "con sao",
            "can gi",
            "o dau",
            "bao gio",
            "ngay nao",
            "ap dung khoa nao",
            "ap dung khoa may",
            "link dau",
        }
        if normalized in follow_up_phrases:
            return True
        if any(phrase in normalized for phrase in follow_up_phrases):
            return True
        if len(tokens) <= 4:
            return True
        if normalized.startswith(("con ", "the ", "vay ", "neu ", "the ielts", "the toeic", "o dau", "bao gio", "can ", "link ")):
            return True
        return False

    def _build_effective_query(self, db: Session, session: ChatSession, content: str) -> str:
        previous_user_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.desc())
            .limit(4)
            .all()
        )
        if not previous_user_messages:
            return content

        current_normalized = self._normalize(content)
        if not self._looks_follow_up(content) and len(current_normalized.split()) >= 5:
            return content

        context_parts: list[str] = []
        for message in reversed(previous_user_messages[:2]):
            if self._normalize(message.content) == current_normalized:
                continue
            context_parts.append(message.content.strip())

        if not context_parts:
            return content
        return " | ".join([*context_parts, content.strip()])

    def _system_prompt(self, db: Session, key: str, fallback: str) -> str:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            return str(config.value_json.get("prompt", fallback))
        return fallback

    def _category_guidance(self, category: str) -> str:
        if category == "WELLBEING":
            return (
                "Đây là một lượt TƯ VẤN TÂM LÝ mức ĐỒNG HÀNH cho sinh viên. Hãy đóng vai một người bạn "
                "biết lắng nghe, dùng kỹ năng tham vấn cơ bản. RANH GIỚI BẮT BUỘC: bạn KHÔNG phải bác sĩ/nhà "
                "trị liệu, KHÔNG chẩn đoán bệnh tâm lý, KHÔNG đưa ra kết luận y khoa hay tên bệnh, KHÔNG kê thuốc.\n"
                "BƯỚC 1 — PHÂN TÍCH (làm ngầm, không in ra dạng liệt kê khô khan): từ lời người dùng, nhận diện "
                "(a) cảm xúc chủ đạo và mức độ; (b) yếu tố gây căng thẳng (học tập, quan hệ, gia đình, tài chính, "
                "giấc ngủ, cô đơn...); (c) lối nghĩ có thể đang khuếch đại vấn đề (tự trách, vơ đũa cả nắm, thảm hoạ hoá); "
                "(d) nhu cầu thật lúc này (được lắng nghe, được trấn an, hay cần một bước hành động nhỏ).\n"
                "BƯỚC 2 — PHẢN HỒI theo trình tự: CÔNG NHẬN cảm xúc chân thành → PHẢN CHIẾU ngắn điều bạn nghe được "
                "để họ thấy được hiểu → BÌNH THƯỜNG HOÁ nhẹ (nhiều sinh viên cũng trải qua) → đặt MỘT câu hỏi mở "
                "nhẹ nhàng để họ nói thêm → gợi ý 1-2 bước nhỏ, cụ thể, làm được ngay (hít thở, nghỉ ngắn, viết ra, "
                "chia nhỏ việc, nhắn cho một người tin cậy).\n"
                "Giọng ấm, tự nhiên, ngắn, KHÔNG lên lớp, KHÔNG sáo rỗng, KHÔNG phán xét, KHÔNG đổ một danh sách lời "
                "khuyên dài — ở lại với cảm xúc của họ trước. "
                "Nếu thấy dấu hiệu nặng hơn mức đồng hành (mất ngủ kéo dài, tuyệt vọng, mất hứng thú lâu, ý nghĩ làm "
                "hại bản thân), nhẹ nhàng khuyến khích tìm hỗ trợ từ NGƯỜI THẬT: bạn bè/người thân, cố vấn học tập, và "
                "nguồn hỗ trợ tâm lý chính thức của UIT (CTSV); nhắc rằng bạn ở đây đồng hành nhưng không thay thế chuyên gia."
            )
        if category == "PLANNING":
            return (
                "Người dùng đang cần sắp lại việc học hoặc deadline. "
                "Hãy phản hồi theo hướng điều phối công việc: tách việc lớn thành bước nhỏ, sắp theo ưu tiên và đề xuất block thời gian ngắn, thực tế."
            )
        if category == "ANNOUNCEMENT":
            return (
                "Người dùng đang hỏi theo kiểu cập nhật nhanh. "
                "Ưu tiên câu trả lời ngắn, chia ý rõ, nêu mốc thời gian và nhắc nếu thông tin có thể đã cũ."
            )
        if category == "ACADEMIC":
            return (
                "Người dùng đang hỏi học vụ hoặc thủ tục. "
                "Ưu tiên nguồn UIT chính thức, nêu quy trình theo từng bước, chỉ rõ nơi cần liên hệ nếu có, và trả lời đủ ý ngay trong lượt này."
            )
        return (
            "Người dùng đang mở đầu một phiên chat chung. "
            "Giữ giọng thân thiện như một người bạn cùng trường và chủ động giải quyết luôn nhu cầu gần nhất của họ; chỉ hỏi làm rõ khi thật sự thiếu dữ kiện để kết luận."
        )

    def _action_suggestions(self, category: str) -> list[str]:
        if category == "WELLBEING":
            return [
                "Nói thêm cho mình biết điều đang làm bạn nặng đầu nhất lúc này.",
                "Nếu muốn, mình có thể giúp bạn tách tuần này thành vài việc nhỏ dễ bắt đầu hơn.",
                "Bạn cũng có thể lưu một dòng ngắn ở mục Nhật ký để Studify nhìn nhịp năng lượng của bạn rõ hơn.",
            ]
        if category == "PLANNING":
            return [
                "Nếu muốn, mình có thể chia tiếp phần việc này theo thứ tự làm trong hôm nay.",
                "Bạn cũng có thể mở Planner để tạo luôn các deadline vừa nhắc tới.",
                "Nếu đang bị ngợp, mình có thể gom lại thành 3 việc quan trọng nhất trước.",
            ]
        if category == "ACADEMIC":
            return [
                "Mở Trung tâm học vụ để xem thêm tài liệu liên quan.",
                "Lưu thông báo quan trọng để đọc lại sau.",
                "Nếu bạn đang bị nhiều deadline dồn, mình có thể giúp chia lại kế hoạch tuần ngay trong khung chat này.",
            ]
        if category == "ANNOUNCEMENT":
            return [
                "Lưu thông báo này để đọc lại sau.",
                "Nếu muốn, mình có thể tóm tắt tiếp các mốc quan trọng nhất trong tuần này.",
                "Bạn cũng có thể hỏi tiếp theo kiểu: còn hạn nào gần nhất hoặc thủ tục nào liên quan?",
            ]
        return [
            "Bạn có thể hỏi mình về học vụ, thông báo, lịch thi, học phí hoặc cách sắp lại tuần này.",
            "Nếu hôm nay bạn thấy hơi mệt, cứ nói thẳng tình trạng hiện tại, mình sẽ đổi cách hỗ trợ cho phù hợp.",
            "Nếu cần, mình có thể tóm tắt lại thành các bước ngắn để bạn dễ làm tiếp.",
        ]

    def _is_crisis_turn(self, analysis: QueryAnalysis) -> bool:
        return analysis.category == "WELLBEING" and analysis.is_urgent and analysis.risk_score >= 0.8

    def _passed_credit_total(self, user: User) -> int | None:
        profile = user.student_profile
        academic = profile.academic_profile if profile else None
        if not academic:
            return None

        passed_course_ids: set[int] = set()
        total = 0
        for record in academic.course_records:
            if record.status not in {CourseRecordStatus.PASSED.value, CourseRecordStatus.WAIVED.value}:
                continue
            if record.course_id in passed_course_ids or not record.course:
                continue
            passed_course_ids.add(record.course_id)
            total += record.course.credits
        return total

    def _credit_total_for_statuses(self, user: User, statuses: set[str]) -> int | None:
        profile = user.student_profile
        academic = profile.academic_profile if profile else None
        if not academic:
            return None

        seen_course_ids: set[int] = set()
        total = 0
        for record in academic.course_records:
            if record.status not in statuses or record.course_id in seen_course_ids or not record.course:
                continue
            seen_course_ids.add(record.course_id)
            total += record.course.credits
        return total

    def _gpa_level_label(self, value: float | None) -> str | None:
        if value is None:
            return None
        if value >= 9.0:
            return "rất xuất sắc"
        if value >= 8.0:
            return "rất ổn, đang ở vùng giỏi trên thang 10"
        if value >= 7.0:
            return "khá ổn, nhưng vẫn còn dư địa để kéo lên"
        if value >= 6.5:
            return "tạm ổn, nên theo dõi kỹ các môn nhiều tín chỉ"
        return "đang cần chú ý vì dễ rơi vào vùng rủi ro học tập"

    def _gpa_assessment_answer(
        self,
        *,
        academic,
        passed_credits: int | None,
        required_credits: int | None,
        in_progress_credits: int | None,
    ) -> str:
        cumulative = academic.cumulative_gpa
        current = academic.current_gpa
        lines: list[str] = []

        if cumulative is not None:
            level = self._gpa_level_label(cumulative)
            lines.append(f"Nhìn tổng thể là **ổn**: GPA tích lũy của bạn đang là **{cumulative:.2f}/10**, {level}.")
        if current is not None:
            lines.append(f"GPA học kỳ gần nhất có điểm là **{current:.2f}/10**.")

        if cumulative is not None and current is not None:
            diff = round(current - cumulative, 2)
            if diff >= 0.2:
                lines.append(f"Học kỳ gần nhất cao hơn tích lũy **{diff:.2f} điểm**, tức là nhịp học đang kéo GPA lên.")
            elif diff <= -0.2:
                lines.append(
                    f"Học kỳ gần nhất thấp hơn tích lũy **{abs(diff):.2f} điểm**. Đây là dấu hiệu hơi chững lại, "
                    f"nhưng **{current:.2f} vẫn là mức tốt**, chưa phải vùng đáng lo."
                )
            else:
                lines.append("Học kỳ gần nhất gần như giữ được nhịp với GPA tích lũy, nên xu hướng hiện tại khá ổn định.")

        if passed_credits is not None and required_credits is not None:
            lines.append(f"Về tiến độ, bạn đã đạt/miễn **{passed_credits}/{required_credits} tín chỉ**.")
        if in_progress_credits:
            lines.append(
                f"Bạn đang học thêm **{in_progress_credits} tín chỉ**; nếu muốn giữ GPA quanh **8.6+**, "
                "nên ưu tiên các môn 3-4 tín chỉ và cố giữ phần lớn môn ở khoảng **8.5-9.0**."
            )

        lines.append(
            "Kết luận ngắn: **không đáng lo**. Nếu mục tiêu là học bổng hoặc xếp loại thật cao thì bạn nên theo dõi tiêu chí chính thức của UIT, "
            "còn về học lực hiện tại thì hồ sơ đang đẹp."
        )
        lines.append("Dữ liệu này lấy từ hồ sơ học vụ trong Studify; khi làm thủ tục chính thức vẫn nên đối chiếu portal UIT.")
        return "\n\n".join(lines)

    def _current_time_answer(self, effective_query: str) -> str | None:
        normalized = self._normalize(effective_query)
        if not normalized:
            return None

        asks_time = self._has_any(
            normalized,
            [
                "bay gio la may gio",
                "bay gio may gio",
                "hien tai may gio",
                "gio hien tai",
                "may gio roi",
                "dang la may gio",
                "luc nay may gio",
            ],
        )
        asks_date = self._has_any(
            normalized,
            [
                "hom nay la ngay may",
                "hom nay ngay may",
                "bay gio la ngay nao",
                "hom nay thu may",
                "ngay hien tai",
                "hom nay la thu may",
            ],
        )
        if not asks_time and not asks_date:
            return None

        now = datetime.now(VIETNAM_TIMEZONE)
        weekday = [
            "Thứ Hai",
            "Thứ Ba",
            "Thứ Tư",
            "Thứ Năm",
            "Thứ Sáu",
            "Thứ Bảy",
            "Chủ Nhật",
        ][now.weekday()]
        if asks_time and asks_date:
            return f"Bây giờ là **{now:%H:%M}**, {weekday}, ngày **{now:%d-%m-%Y}** theo giờ Việt Nam (UTC+7)."
        if asks_date:
            return f"Hôm nay là **{weekday}, ngày {now:%d-%m-%Y}** theo giờ Việt Nam (UTC+7)."
        return f"Bây giờ là **{now:%H:%M}** ngày **{now:%d-%m-%Y}** theo giờ Việt Nam (UTC+7)."

    def _is_general_direct_turn(self, analysis: QueryAnalysis, effective_query: str) -> bool:
        if analysis.category != "GENERAL":
            return False
        if self._is_default_uit_school_context_query(effective_query):
            return False
        if self._is_next_course_planning_query(effective_query):
            return False
        return "personal_academic" not in self._query_topics(effective_query)

    def _is_next_course_planning_query(self, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if not normalized:
            return False
        course_markers = [
            "mon",
            "hoc phan",
            "ctdt",
            "chuong trinh",
            "lo trinh",
            "ke hoach hoc tap",
        ]
        planning_markers = [
            "nen hoc",
            "hoc tiep",
            "tiep theo",
            "dang ky mon nao",
            "dang ky hoc phan nao",
            "mon nen dang ky",
            "mon con lai",
            "hoc phan con lai",
            "theo chuong trinh",
            "theo ctdt",
        ]
        return self._has_any(normalized, course_markers) and self._has_any(normalized, planning_markers)

    def _is_quick_no_web_query(self, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if not normalized:
            return True
        if self._current_time_answer(effective_query):
            return True

        tokens = normalized.split()
        greetings = {
            "hi",
            "hello",
            "hey",
            "xin chao",
            "chao",
            "chao ban",
            "he lo",
            "he lu",
            "alo",
            "cam on",
            "thanks",
            "thank you",
            "ok",
            "oke",
            "okay",
        }
        if normalized in greetings:
            return True
        if len(tokens) <= 3 and self._has_any(normalized, ["xin chao", "chao", "hello", "hi", "he lo", "he lu"]):
            return True

        assistant_smalltalk = {
            "ban la ai",
            "ban ten gi",
            "ten ban la gi",
            "studify la gi",
            "ban lam duoc gi",
            "ban giup gi duoc",
        }
        if normalized in assistant_smalltalk:
            return True

        if re.fullmatch(r"[0-9\s+\-*/().=]+", normalized):
            return True
        if len(tokens) <= 8 and self._has_any(
            normalized,
            [
                "cong",
                "tru",
                "nhan",
                "chia",
                "bang may",
                "la bao nhieu",
                "tinh giup",
            ],
        ) and any(char.isdigit() for char in normalized):
            return True

        return False

    def _general_direct_needs_web_search(self, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if not normalized:
            return False
        return not self._is_quick_no_web_query(effective_query)

    def _fallback_search_queries(self, effective_query: str, max_queries: int) -> list[str]:
        normalized = self._normalize(effective_query)
        queries: list[str] = []
        if self._has_any(normalized, ["nsu crypto", "nsucrypto"]):
            years = re.findall(r"\b20\d{2}\b", effective_query) or [str(datetime.now(VIETNAM_TIMEZONE).year)]
            for year in years:
                queries.extend(
                    [
                        f"NSUCRYPTO {year} UIT đạt giải",
                        f"site:ctsv.uit.edu.vn NSUCRYPTO {year} UIT",
                        f"site:uit.edu.vn NSUCRYPTO {year} UIT",
                    ]
                )
        if self._has_any(
            normalized,
            [
                "truong khoa mang may tinh",
                "truong khoa truyen thong",
                "ban chu nhiem khoa mang",
                "mang may tinh va truyen thong",
                "mmt tt",
                "nc uit",
            ],
        ):
            queries.extend(
                [
                    'site:nc.uit.edu.vn "Ban chủ nhiệm khoa" "Trưởng khoa"',
                    'site:nc.uit.edu.vn "Khoa Mạng máy tính và Truyền thông" "Trưởng khoa"',
                ]
            )
        if self._asks_official_graduation_requirements(effective_query):
            queries.extend(
                [
                    'site:student.uit.edu.vn "xét tốt nghiệp" "điều kiện"',
                    'site:daa.uit.edu.vn "điều kiện tốt nghiệp" UIT',
                    'site:student.uit.edu.vn "đăng ký xét tốt nghiệp" UIT',
                    'site:uit.edu.vn "điều kiện tốt nghiệp" "UIT"',
                ]
            )
        queries.append(effective_query)

        unique: list[str] = []
        seen: set[str] = set()
        for query in queries:
            key = self._normalize(query)
            if query.strip() and key not in seen:
                seen.add(key)
                unique.append(query.strip())
            if len(unique) >= max_queries:
                break
        return unique

    def _search_planner_messages(self, effective_query: str, analysis: QueryAnalysis, max_queries: int) -> list[dict[str, str]]:
        now = datetime.now(VIETNAM_TIMEZONE)
        return [
            {
                "role": "system",
                "content": (
                    "Bạn là search planner của Studify. Nhiệm vụ duy nhất: phân tích câu hỏi và tạo kế hoạch tìm kiếm web; "
                    "KHÔNG trả lời câu hỏi. Chỉ trả JSON hợp lệ, không markdown, không giải thích ngoài JSON. "
                    "Schema: {\"needs_web_search\": boolean, \"queries\": string[], \"reason\": string}. "
                    f"Tối đa {max_queries} queries, query ngắn nhưng đủ từ khóa. "
                    "Mặc định ngữ cảnh trường là UIT nếu người dùng không nêu trường khác. "
                    "Không tự thêm cú pháp site: cho câu hỏi UIT; backend sẽ tự ưu tiên daa.uit.edu.vn, oep.uit.edu.vn, ctsv.uit.edu.vn trước. "
                    "Nếu có khả năng thông tin nằm ở trang chính/khoa/phòng lab, thêm một query mở rộng bằng từ khóa tự nhiên, không dùng site:. "
                    "Với câu hỏi nhân sự khoa/phòng ban UIT như trưởng khoa, phó trưởng khoa, ban chủ nhiệm khoa, "
                    "ưu tiên từ khóa Ban chủ nhiệm khoa, tên khoa/phòng ban và domain khoa liên quan trong query tự nhiên; "
                    "riêng Khoa Mạng máy tính và Truyền thông thường nằm ở nc.uit.edu.vn. "
                    "Chỉ dùng site: khi người dùng hỏi trường khác và bạn biết domain chính thức của trường đó. "
                    "Với NSU Crypto, chuẩn hóa thêm từ khóa NSUCRYPTO và Olympic Mật mã học quốc tế. "
                    "Với câu dễ như chào hỏi, hỏi giờ/ngày hiện tại, phép tính đơn giản thì needs_web_search=false. "
                    f"Thời điểm hiện tại: {now:%d/%m/%Y %H:%M:%S} UTC+7. "
                    f"Phân loại sơ bộ: {analysis.category}."
                ),
            },
            {"role": "user", "content": effective_query},
        ]

    def _parse_search_plan(self, raw: str, effective_query: str, max_queries: int) -> SearchPlan:
        fallback = self._fallback_search_queries(effective_query, max_queries)
        text = (raw or "").strip()
        if not text:
            return SearchPlan(True, fallback, "Planner rỗng, dùng query fallback.")

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("[chat] không parse được search plan JSON: %s", raw[:500])
            return SearchPlan(True, fallback, "Planner không trả JSON hợp lệ.")

        if not isinstance(data, dict):
            return SearchPlan(True, fallback, "Planner không trả object JSON.")

        needs = bool(data.get("needs_web_search", True))
        if not needs:
            return SearchPlan(False, [], str(data.get("reason", "") or "Planner đánh dấu không cần web."))

        raw_queries = data.get("queries", [])
        if isinstance(raw_queries, str):
            raw_queries = [raw_queries]
        queries: list[str] = []
        seen: set[str] = set()
        for item in raw_queries if isinstance(raw_queries, list) else []:
            query = str(item).strip()
            key = self._normalize(query)
            if not query or key in seen:
                continue
            seen.add(key)
            queries.append(query)
            if len(queries) >= max_queries:
                break
        if not queries:
            queries = fallback
        return SearchPlan(True, queries[:max_queries], str(data.get("reason", "") or ""))

    async def _plan_web_search(self, effective_query: str, analysis: QueryAnalysis, max_queries: int) -> SearchPlan:
        if self._is_quick_no_web_query(effective_query):
            return SearchPlan(False, [], "Câu hỏi nhanh không cần web.")
        try:
            raw = await self.llm.chat(
                self._search_planner_messages(effective_query, analysis, max_queries),
                web_search_enabled=False,
            )
            plan = self._parse_search_plan(raw, effective_query, max_queries)
        except Exception as exc:
            logger.warning("[chat] search planner thất bại: %s", exc)
            plan = SearchPlan(True, self._fallback_search_queries(effective_query, max_queries), "Planner lỗi, dùng query fallback.")
        if plan.needs_web_search and not plan.queries:
            plan.queries = self._fallback_search_queries(effective_query, max_queries)
        return plan

    async def _execute_search_plan(self, plan: SearchPlan, *, max_results: int) -> str:
        if not plan.needs_web_search or not plan.queries:
            return ""

        from app.services.web_search_service import WebSearchService

        service = WebSearchService()
        sections: list[str] = []
        for index, query in enumerate(plan.queries, start=1):
            try:
                result = await service.search(query, max_results=max_results)
            except Exception as exc:
                logger.warning("[chat] web_search planner query thất bại '%s': %s", query, exc)
                result = f"Không tìm kiếm được query này: {exc}"
            sections.append(f"[Search query {index}] {query}\n{result[:7000]}")
            if self._search_result_is_useful(result):
                break

        combined = "\n\n".join(sections).strip()
        return combined[:24000]

    def _search_result_is_useful(self, result: str) -> bool:
        normalized = self._normalize(result)
        if not normalized or "khong tim thay ket qua nao" in normalized or "khong tim kiem duoc" in normalized:
            return False
        return "nguon" in normalized and len(normalized.split()) >= 120

    def _messages_with_search_results(
        self,
        messages: list[dict[str, str]],
        effective_query: str,
        plan: SearchPlan,
        search_results: str,
    ) -> list[dict[str, str]]:
        if not plan.needs_web_search:
            return messages
        content = (
            "Backend đã thực hiện web_search theo kế hoạch tìm kiếm trước khi tổng hợp. "
            "Không gọi web_search nữa trong lượt này. Hãy trả lời trực tiếp câu hỏi của người dùng dựa trên kết quả dưới đây, "
            "RAG/hồ sơ Studify nếu có, và kiến thức GPT hiện có. Nếu kết quả web không đủ hoặc không tìm thấy dữ liệu, "
            "vẫn trả lời phần có thể bằng kiến thức GPT, nhưng nói rõ phần đó chưa xác minh được bằng web search. "
            "Không kết thúc bằng yêu cầu người dùng gửi link trừ khi câu hỏi không thể hiểu được.\n\n"
            f"Câu hỏi đầy đủ: {effective_query}\n"
            f"Lý do/kế hoạch: {plan.reason or 'Không có'}\n\n"
            f"Kết quả web_search:\n{search_results or 'Không có kết quả web_search hữu ích.'}"
        )
        return [*messages, {"role": "system", "content": content}]

    def _general_direct_messages(self, db: Session, session: ChatSession, content: str, *, needs_web_search: bool = False) -> list[dict[str, str]]:
        now = datetime.now(VIETNAM_TIMEZONE)
        web_instruction = (
            "Câu này không phải chào hỏi/câu trả lời nhanh; bắt buộc gọi web_search trước khi kết luận, "
            "ưu tiên tìm trên daa.uit.edu.vn, oep.uit.edu.vn, ctsv.uit.edu.vn trước các nguồn khác, "
            "và nêu rõ mốc thời gian áp dụng khi phù hợp. Nếu web_search không tìm thấy, trả lời trực tiếp bằng kiến thức GPT hiện có, "
            "nói rõ là chưa xác minh được bằng web; không dừng ở việc yêu cầu người dùng gửi link. "
            if needs_web_search
            else "Không cần web_search nếu câu hỏi có thể trả lời bằng kiến thức chung hoặc thời gian server đã cung cấp. "
        )
        system = (
            "Bạn là GPT trả lời trực tiếp các câu hỏi ngoài lề trong Studify. "
            "Không dùng pipeline học vụ, không tra RAG, không bịa nguồn UIT, không yêu cầu sinh viên mở mục Học vụ/Thông báo. "
            f"Thời gian hiện tại của server là {now:%H:%M:%S}, ngày {now:%d-%m-%Y}, múi giờ Việt Nam UTC+7. "
            "Nếu người dùng hỏi giờ hoặc ngày hiện tại, trả lời theo thời gian này. "
            f"{web_instruction}"
            "Câu dễ thì trả lời nhanh, tự nhiên, đúng trọng tâm; câu cần giải thích thì thêm lý do ngắn. "
            "Nếu không chắc vì thiếu dữ liệu thời sự hoặc dữ liệu cá nhân, nói rõ giới hạn thay vì đoán."
        )
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.desc())
            .limit(8)
            .all()
        )
        messages = [{"role": "system", "content": system}]
        for message in reversed(history):
            messages.append({"role": "assistant" if message.role == "assistant" else "user", "content": message.content})
        if not any(message["role"] == "user" and message["content"] == content for message in messages):
            messages.append({"role": "user", "content": content})
        return messages

    def _general_direct_fallback(self, effective_query: str) -> str:
        time_answer = self._current_time_answer(effective_query)
        if time_answer:
            return time_answer
        return "Mình chưa suy nghĩ trọn vẹn được cho câu ngoài lề này. Bạn thử gửi lại sau một chút."

    def _missing_required_courses(self, user: User, limit: int = 8) -> list[str]:
        profile = user.student_profile
        academic = profile.academic_profile if profile else None
        program = academic.program if academic else None
        if not academic or not program:
            return []

        completed_or_learning_ids = {
            record.course_id
            for record in academic.course_records
            if record.status
            in {
                CourseRecordStatus.PASSED.value,
                CourseRecordStatus.WAIVED.value,
                CourseRecordStatus.IN_PROGRESS.value,
            }
        }
        missing: list[str] = []
        for requirement in sorted(program.requirements, key=lambda item: (item.recommended_semester, item.course.code if item.course else "")):
            if not requirement.is_required or requirement.course_id in completed_or_learning_ids or not requirement.course:
                continue
            missing.append(f"{requirement.course.code} - {requirement.course.name} ({requirement.course.credits} tín chỉ)")
            if len(missing) >= limit:
                break
        return missing

    def _course_record_lines(self, user: User, statuses: set[str], limit: int = 8) -> list[str]:
        profile = user.student_profile
        academic = profile.academic_profile if profile else None
        if not academic:
            return []

        lines: list[str] = []
        seen_course_ids: set[int] = set()
        records = sorted(
            academic.course_records,
            key=lambda item: (item.semester_code, item.course.code if item.course else ""),
            reverse=True,
        )
        for record in records:
            if record.status not in statuses or not record.course or record.course_id in seen_course_ids:
                continue
            seen_course_ids.add(record.course_id)
            grade = ""
            if record.numeric_grade is not None:
                grade = f", điểm {record.numeric_grade:g}"
            elif record.letter_grade:
                grade = f", điểm {record.letter_grade}"
            lines.append(
                f"{record.course.code} - {record.course.name} "
                f"({record.course.credits} tín chỉ, {record.semester_code}{grade})"
            )
            if len(lines) >= limit:
                break
        return lines

    def _user_context_brief(self, db: Session, user: User) -> str | None:
        del db
        profile = user.student_profile
        if not profile:
            return None

        lines = [
            "Thông tin sinh viên đang hỏi:",
            f"- Họ tên: {user.full_name}",
            f"- MSSV: {profile.student_id}",
            f"- Ngành: {profile.major}, Khoa: {profile.faculty}",
            f"- Lớp: {profile.class_name}, Khóa: {profile.cohort}",
        ]

        academic = profile.academic_profile
        if academic:
            lines.append(f"- Học kỳ tiến độ hiện tại trong hồ sơ: {academic.current_semester_index}")
            lines.append(f"- Mục tiêu tín chỉ mỗi kỳ: {academic.target_credits_per_term}")
            if academic.cumulative_gpa is not None:
                lines.append(f"- GPA tích lũy hiện tại: {academic.cumulative_gpa:.2f}")
            if academic.current_gpa is not None:
                lines.append(f"- GPA học kỳ hiện tại: {academic.current_gpa:.2f}")
            passed_credits = self._passed_credit_total(user)
            if passed_credits is not None:
                lines.append(f"- Tín chỉ đã tích lũy: {passed_credits}")
            if academic.program:
                required_credits = academic.program.total_required_credits
                lines.append(f"- Chương trình: {academic.program.name} (yêu cầu {required_credits} tín chỉ)")
                if passed_credits is not None:
                    remaining = max(0, required_credits - passed_credits)
                    lines.append(f"- Tín chỉ còn cần hoàn thành: {remaining}")
                if academic.program.english_requirement:
                    lines.append(f"- Chuẩn ngoại ngữ của chương trình: {academic.program.english_requirement}")
            if academic.expected_graduation_term:
                lines.append(f"- Dự kiến tốt nghiệp: {academic.expected_graduation_term}")

        in_progress_courses = self._course_record_lines(user, {CourseRecordStatus.IN_PROGRESS.value}, limit=8)
        if in_progress_courses:
            lines.append("- Học phần đang học theo hồ sơ:")
            lines.extend(f"  + {item}" for item in in_progress_courses)

        planned_courses = self._course_record_lines(user, {CourseRecordStatus.PLANNED.value}, limit=5)
        if planned_courses:
            lines.append("- Học phần đã lên kế hoạch theo hồ sơ:")
            lines.extend(f"  + {item}" for item in planned_courses)

        missing_courses = self._missing_required_courses(user, limit=12)
        if missing_courses:
            lines.append("- Một số học phần bắt buộc chưa hoàn thành hoặc chưa học theo hồ sơ:")
            lines.extend(f"  + {item}" for item in missing_courses)

        lines.append(
            "Khi sinh viên hỏi về thông tin cá nhân như GPA, tín chỉ, tiến độ tốt nghiệp hoặc chương trình đang học, "
            "ưu tiên dùng dữ liệu trên thay vì yêu cầu sinh viên cung cấp lại."
        )
        return "\n".join(lines)

    def _course_planning_brief(self, user: User | None, effective_query: str) -> str | None:
        if not self._is_next_course_planning_query(effective_query):
            return None

        profile = user.student_profile if user else None
        academic = profile.academic_profile if profile else None
        program = academic.program if academic else None
        student_context = ""
        if profile:
            student_context = (
                f"Sinh viên đang hỏi thuộc ngành {profile.major}, lớp {profile.class_name}, "
                f"khóa {profile.cohort}."
            )
        if program:
            student_context += f" Chương trình trong hồ sơ: {program.name}, tổng {program.total_required_credits} tín chỉ."

        return (
            "Câu này yêu cầu gợi ý học phần nên học tiếp theo theo chương trình học/CTĐT. "
            f"{student_context} "
            "Bắt buộc dùng hồ sơ sinh viên trong system context và gọi web_search để đối chiếu nguồn UIT công khai "
            "về CTĐT, học phần tiên quyết, kế hoạch đào tạo hoặc đăng ký học phần trước khi chốt. "
            "Ưu tiên tìm trên daa.uit.edu.vn, oep.uit.edu.vn, ctsv.uit.edu.vn trước, rồi mới đến student.uit.edu.vn, courses.uit.edu.vn và uit.edu.vn. "
            "Nếu web_search không tìm được nguồn chính thức đúng ngành/khóa thì nói rõ phần nào dựa trên hồ sơ Studify "
            "và phần nào chưa xác minh được từ UIT. "
            "Nếu chưa trích xuất được bảng môn hoặc mã học phần cụ thể từ nguồn UIT/web_search, không được bịa mã môn hoặc tên môn mới; "
            "hãy nói rõ chưa xác minh được mã môn cụ thể và chỉ đưa nhóm ưu tiên ở mức định hướng. "
            "Không đề xuất đăng ký lại các học phần đang học; chỉ dùng chúng làm tiền đề để suy luận hướng tiếp theo. "
            "Trả lời theo cấu trúc: kết luận ngắn; 3-6 học phần nên ưu tiên; lý do chọn từng môn; lưu ý rủi ro/tiên quyết/tải tín chỉ."
        )

    def _asks_official_graduation_requirements(self, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if "graduation" not in self._query_topics(effective_query):
            return False
        return self._has_any(
            normalized,
            [
                "yeu cau tot nghiep",
                "dieu kien tot nghiep",
                "quy dinh tot nghiep",
                "xet tot nghiep",
                "ho so tot nghiep",
                "cong nhan tot nghiep",
                "ra truong can gi",
                "can gi de tot nghiep",
                "tieu chuan tot nghiep",
            ],
        )

    def _should_fast_personal_academic_answer(self, effective_query: str) -> bool:
        if "personal_academic" not in self._query_topics(effective_query):
            return False
        if self._is_next_course_planning_query(effective_query):
            return False
        if self._asks_official_graduation_requirements(effective_query):
            return False
        return True

    def _graduation_personal_brief(self, user: User | None, effective_query: str) -> str | None:
        if not self._asks_official_graduation_requirements(effective_query):
            return None
        if "personal_academic" not in self._query_topics(effective_query):
            return None

        profile = user.student_profile if user else None
        academic = profile.academic_profile if profile else None
        if not profile or not academic:
            return None

        lines = [
            "Câu hỏi này có 2 phần và KHÔNG được trả lời bằng fast answer cá nhân đơn giản:",
            "1) Tiến độ cá nhân của sinh viên theo hồ sơ Studify.",
            "2) Yêu cầu/điều kiện tốt nghiệp UIT theo nguồn chính thức hoặc web_search.",
        ]

        passed_credits = self._passed_credit_total(user)
        program = academic.program
        if passed_credits is not None:
            lines.append(f"- Tín chỉ đã tích lũy theo hồ sơ: {passed_credits}.")
        if program:
            required_credits = program.total_required_credits
            lines.append(f"- Chương trình trong hồ sơ: {program.name}, yêu cầu {required_credits} tín chỉ.")
            if passed_credits is not None:
                lines.append(f"- Tín chỉ còn cần hoàn thành theo hồ sơ: {max(0, required_credits - passed_credits)}.")
            if program.english_requirement:
                lines.append(f"- Chuẩn ngoại ngữ trong hồ sơ/chương trình: {program.english_requirement}.")
        if academic.cumulative_gpa is not None:
            lines.append(f"- GPA tích lũy hiện tại: {academic.cumulative_gpa:.2f}.")

        lines.extend(
            [
                "Khi trả lời, mở đầu bằng số tín chỉ còn thiếu của sinh viên, rồi tách mục yêu cầu tốt nghiệp UIT.",
                "Bắt buộc nêu rõ phần tín chỉ/GPA là dữ liệu trong Studify; phần yêu cầu tốt nghiệp phải dựa trên nguồn UIT/web_search nếu có.",
            ]
        )
        return "\n".join(lines)

    def _personal_academic_answer(self, db: Session, user: User | None, effective_query: str) -> str | None:
        del db
        if not user or "personal_academic" not in self._query_topics(effective_query):
            return None

        profile = user.student_profile
        academic = profile.academic_profile if profile else None
        if not profile:
            return "Mình chưa thấy hồ sơ sinh viên gắn với tài khoản này nên chưa thể đọc GPA, tín chỉ hoặc tiến độ tốt nghiệp cá nhân."
        if not academic:
            return (
                f"Mình đã nhận diện bạn là {user.full_name} ({profile.student_id}), "
                "nhưng hồ sơ học vụ chi tiết chưa có dữ liệu chương trình, GPA hoặc tín chỉ tích lũy."
            )

        normalized = self._normalize(effective_query)
        program = academic.program
        passed_credits = self._passed_credit_total(user)
        required_credits = program.total_required_credits if program else None
        remaining_credits = max(0, required_credits - (passed_credits or 0)) if required_credits is not None else None

        if self._is_next_course_planning_query(effective_query):
            return None

        if self._has_any(normalized, ["gpa", "diem trung binh"]):
            if academic.cumulative_gpa is not None or academic.current_gpa is not None:
                in_progress_credits = self._credit_total_for_statuses(user, {CourseRecordStatus.IN_PROGRESS.value})
                return self._gpa_assessment_answer(
                    academic=academic,
                    passed_credits=passed_credits,
                    required_credits=required_credits,
                    in_progress_credits=in_progress_credits,
                )
            return "Hồ sơ của bạn chưa có dữ liệu GPA để Studify trả lời chính xác."

        if self._has_any(normalized, ["chuong trinh gi", "dang hoc chuong trinh", "nganh gi", "lop nao"]):
            answer = (
                f"Bạn đang học **{profile.major}** thuộc **{profile.faculty}**, lớp **{profile.class_name}**, khóa **{profile.cohort}**."
            )
            if program:
                answer += f" Chương trình đang gắn trong hệ thống là **{program.name}**."
            if academic.expected_graduation_term:
                answer += f" Dự kiến tốt nghiệp: **{academic.expected_graduation_term}**."
            return answer

        if self._has_any(normalized, ["mon gi", "hoc them mon", "can hoc them", "con thieu mon"]):
            missing_courses = self._missing_required_courses(user, limit=10)
            if not missing_courses:
                return (
                    "Theo hồ sơ hiện có, Studify chưa thấy học phần bắt buộc nào còn thiếu rõ ràng. "
                    "Bạn vẫn nên đối chiếu thêm CTĐT chính thức, chuẩn ngoại ngữ và các điều kiện xét tốt nghiệp mới nhất của UIT."
                )
            course_lines = "\n".join(f"- {item}" for item in missing_courses)
            credit_line = ""
            if remaining_credits is not None:
                credit_line = f"\n\nTổng tín chỉ còn cần hoàn thành theo chương trình: **{remaining_credits} tín chỉ**."
            return (
                "Theo hồ sơ học vụ của bạn, các học phần bắt buộc nên ưu tiên kiểm tra tiếp là:\n\n"
                f"{course_lines}"
                f"{credit_line}\n\n"
                "Danh sách này dựa trên dữ liệu mô phỏng trong Studify; khi làm hồ sơ tốt nghiệp, bạn vẫn cần đối chiếu CTĐT và thông báo chính thức của Phòng Đào tạo."
            )

        if self._has_any(normalized, ["tin", "tin chi", "tot nghiep", "con thieu", "bao nhieu"]):
            if passed_credits is None or required_credits is None or remaining_credits is None:
                return "Hồ sơ của bạn chưa đủ dữ liệu tín chỉ hoặc chương trình đào tạo để tính số tín chỉ còn thiếu."
            answer = (
                f"Theo hồ sơ học vụ của bạn, bạn đã tích lũy **{passed_credits}/{required_credits} tín chỉ**. "
                f"Bạn còn cần khoảng **{remaining_credits} tín chỉ** để đạt yêu cầu tín chỉ của chương trình."
            )
            if academic.cumulative_gpa is not None:
                answer += f" GPA tích lũy hiện tại là **{academic.cumulative_gpa:.2f}**."
            if program and program.english_requirement:
                answer += f" Ngoài tín chỉ, bạn cần kiểm tra thêm chuẩn ngoại ngữ: **{program.english_requirement}**."
            answer += " Đây là dữ liệu hồ sơ trong Studify, chưa thay thế kết quả xác nhận chính thức từ UIT."
            return answer

        return None

    def _crisis_action_suggestions(self) -> list[str]:
        return [
            "Rời xa ngay các vật có thể gây hại và đi tới nơi có người ở gần.",
            "Nhắn hoặc gọi cho một người bạn tin cậy với câu: 'Mình đang không an toàn, ở cạnh mình được không?'",
            "Nếu có nguy cơ trước mắt, gọi cấp cứu địa phương hoặc đến cơ sở y tế gần nhất ngay.",
        ]

    def _crisis_answer(self) -> str:
        return (
            "Mình rất lo khi nghe bạn nói vậy. Lúc này ưu tiên số một là giữ bạn an toàn ngay trong vài phút tới.\n\n"
            "- Nếu bạn có thể làm hại bản thân hoặc đang ở nguy hiểm trước mắt, hãy gọi cấp cứu địa phương ngay "
            "(ví dụ 115 tại Việt Nam) hoặc đến cơ sở y tế gần nhất.\n"
            "- Nếu có thể, hãy đi tới nơi có người ở gần, rời xa các vật có thể gây hại, và nhắn cho một người bạn tin cậy, "
            "người thân, cố vấn học tập hoặc người phụ trách gần bạn: \"Mình đang không an toàn, ở cạnh mình được không?\"\n"
            "- Nếu bạn đang ở UIT, hãy tìm hỗ trợ trực tiếp từ người của trường như CTSV, cố vấn học tập, bảo vệ, ký túc xá "
            "hoặc thầy cô gần nhất. Đừng ở một mình với cảm giác này.\n\n"
            "Mình không phải bác sĩ hay nhà trị liệu, nhưng mình có thể ở đây cùng bạn trong lúc bạn gọi hoặc nhắn cho người thật. "
            "Bây giờ bạn chỉ cần trả lời thật ngắn: bạn đang ở một mình hay có ai ở gần?"
        )

    def _should_low_confidence_refuse(self, prepared: PreparedTurn) -> bool:
        return prepared.analysis.category in {"ACADEMIC", "ANNOUNCEMENT"} and not prepared.contexts and not prepared.facts

    def _low_confidence_answer(self) -> str:
        return "Mình chưa tìm thấy nguồn UIT đủ chắc để trả lời chính xác câu này."

    def _fallback_answer(self, category: str, contexts: list[RetrievedContext]) -> str:
        if contexts:
            snippets = []
            for item in contexts[:2]:
                source_text = (item.document.summary or item.excerpt or "").strip()
                normalized = " ".join(source_text.split())
                if len(normalized) > 220:
                    normalized = f"{normalized[:217]}..."
                snippets.append(f"- {item.document.title}: {normalized}")
            snippet_block = "\n".join(snippets)
            return (
                "Mình đang gặp trục trặc kết nối AI nên sẽ tóm tắt nhanh từ dữ liệu đã tìm được:\n\n"
                f"{snippet_block}\n\n"
                "Nếu cần, bạn gửi tiếp câu hỏi cụ thể hơn để mình lọc lại thông tin gọn hơn."
            )

        if category == "WELLBEING":
            return (
                "Mình đang gặp trục trặc kết nối AI nên chưa phản hồi sâu như bình thường. "
                "Nếu hôm nay bạn hơi mệt hoặc quá tải, thử nghỉ 5 phút, uống nước, rồi nói cho mình biết việc nào đang nặng đầu nhất để mình cùng tách nhỏ tiếp."
            )
        if category == "PLANNING":
            return (
                "Mình đang gặp trục trặc kết nối AI nên chưa sắp lại giúp bạn trọn vẹn được. "
                "Bạn thử gửi lại theo mẫu: việc gì, hạn khi nào, và việc nào bắt buộc phải xong trước để mình chia nhanh thành từng bước."
            )

        return (
            "Mình đang gặp trục trặc kết nối AI nên chưa tổng hợp trọn vẹn được. "
            "Bạn có thể gửi lại câu hỏi ngắn hơn hoặc mở mục Học vụ/Thông báo để xem nguồn UIT chính thức trước."
        )

    def _should_use_retrieval(self, analysis: QueryAnalysis, effective_query: str) -> bool:
        normalized = self._normalize(effective_query)
        if self._is_crisis_turn(analysis):
            return False
        if self._is_next_course_planning_query(effective_query):
            return True
        if self._is_default_uit_school_context_query(effective_query):
            return True
        if analysis.category in {"ACADEMIC", "ANNOUNCEMENT"}:
            return True
        if analysis.category == "WELLBEING":
            return self._has_any(
                normalized,
                [
                    "ho tro",
                    "tam ly",
                    "tu van",
                    "ctsv",
                    "uit",
                    "nguon luc",
                    "lien he",
                    "o dau",
                    "phong ban",
                    "nguoi that",
                ],
            )
        return False

    def _should_enable_web_search(self, prepared: PreparedTurn) -> bool:
        # Planner-search-synthesis: câu không khủng hoảng có thể được GPT lập query,
        # backend thực hiện web/PDF search, rồi LLM tổng hợp với web_search tool tắt.
        if self._is_crisis_turn(prepared.analysis):
            return False
        return True

    def _direct_answer_rules(self, effective_query: str) -> str:
        normalized = self._normalize(effective_query)
        topics = self._query_topics(effective_query)
        rules = [
            "Luôn trả lời thẳng vào câu hỏi ở ngay câu đầu tiên, không vòng vo.",
            "Nếu câu hỏi mang tính đánh giá như 'ổn không', 'nên làm gì', 'có đáng lo không', không chỉ lặp lại dữ kiện; phải đưa ra nhận định ngắn, lý do chính và một bước nên làm tiếp.",
            "Câu dễ thì trả lời nhanh; câu có dữ liệu cá nhân, học vụ, deadline hoặc khả năng nhầm mốc thì phải cân nhắc ngữ cảnh trước khi kết luận.",
            "Nếu dữ liệu chính thức đã đủ để trả lời ở mức tổng quát, không hỏi ngược lại người dùng về khóa, ngành hay chương trình.",
            "Chỉ hỏi thêm khi thiếu thông tin làm thay đổi kết luận chính.",
            "Nếu có nhiều văn bản, ưu tiên văn bản hiện hành công khai mới nhất và nêu rõ mốc khóa/năm áp dụng.",
            "Không dùng các câu như 'mình chưa tìm thấy', 'mình không có đầy đủ nội dung' nếu ngữ cảnh đã chứa thông tin cần thiết.",
            "Với câu hỏi học vụ, mở đầu bằng kết luận trực tiếp, không đặt tiêu đề 'Trả lời nhanh'; nếu cần chia mục thì dùng: ### Chi tiết, ### Bạn nên làm gì tiếp theo?, ### Nguồn tham khảo.",
            "Trong phần nguồn tham khảo, chỉ dùng URL xuất hiện trong ngữ cảnh đã cung cấp; tuyệt đối không tự tạo link mới.",
            "Ưu tiên định dạng markdown gọn: một kết luận mở đầu, sau đó là các gạch đầu dòng ngắn; chỉ dùng bảng khi thật sự cần so sánh nhiều mức chuẩn.",
            "Không kết thúc bằng câu hỏi ngược nếu bạn đã có thể trả lời trọn ý trong lượt hiện tại.",
            "Không kết thúc bằng lời mời mở rộng kiểu 'bạn cần thêm gì không', 'bạn cần mình hỗ trợ thêm gì', hoặc 'bạn cần thông tin nào khác không'.",
            "Không mời người dùng cung cấp thêm khóa, ngành hay chương trình ở cuối câu trả lời nếu bạn đã nêu đủ các mức chính.",
            "Không viết các câu dạng 'bạn có thể cho mình biết khóa nào', 'nếu bạn cho mình biết khóa', hoặc 'cho mình biết chương trình' khi câu trả lời tổng quát đã đủ dùng.",
        ]
        if "english" in topics:
            rules.extend(
                [
                    "Đây là câu hỏi về chuẩn đầu ra ngoại ngữ. Hãy ưu tiên nêu con số chuẩn đầu ra trước.",
                    "Nếu người dùng hỏi chung 'của trường là gì', hãy trả lời quy định phổ biến nhất đang áp dụng cho khóa mới, rồi bổ sung bảng tóm tắt các khóa cũ hơn nếu dữ liệu có.",
                    "Nếu trong nguồn có cả TOEIC và IELTS tương đương, hãy nêu cả hai, không tự quy đổi bằng bảng ngoài nguồn.",
                    "Nếu người dùng không nêu khóa, mặc định ưu tiên mốc đại trà khóa tuyển 2024 trở về sau là quy định hiện hành phổ biến nhất để mở đầu câu trả lời.",
                    "Không dùng cụm 'khóa 2022 trở về sau' làm kết luận mở đầu cho câu hỏi chung; mốc mở đầu phải là 'khóa tuyển 2024 trở về sau'.",
                    "Sau khi đã nêu đủ các mức 2024+, 2022-2023, 2019-2021, CTTN/CTCLC và CTTT thì dừng lại, không rủ người dùng cung cấp thêm thông tin.",
                ]
            )
        if "registration" in topics:
            rules.extend(
                [
                    "Với câu hỏi về đăng ký học phần, phải nói rõ cổng hoặc bước xác nhận ĐKHP trước, sau đó mới nêu các lưu ý và vi phạm cần tránh.",
                    "Nếu nguồn có mốc xác nhận, hành vi bị cấm hoặc email liên hệ thì phải nêu rõ.",
                ]
            )
        if "tuition" in topics:
            rules.extend(
                [
                    "Với câu hỏi học phí, nêu rõ học kỳ hoặc năm học áp dụng, đối tượng áp dụng, hạn đóng và nơi xem/đóng học phí nếu nguồn có.",
                ]
            )
        if "scholarship" in topics:
            rules.extend(
                [
                    "Với câu hỏi học bổng, nêu rõ loại học bổng, đối tượng, điều kiện chính, các trường hợp không được xét và hạn đăng ký nếu nguồn có.",
                ]
            )
        if "graduation" in topics:
            rules.extend(
                [
                    "Với câu hỏi tốt nghiệp, nêu ngay điều kiện hoặc đợt xét tốt nghiệp hiện tại, sau đó liệt kê hồ sơ hoặc mốc cần theo dõi.",
                ]
            )
            if "personal_academic" in topics and self._asks_official_graduation_requirements(effective_query):
                rules.extend(
                    [
                        "Với câu hỏi vừa hỏi tín chỉ cá nhân vừa hỏi yêu cầu tốt nghiệp UIT, phải trả lời đủ 2 phần: tiến độ cá nhân theo hồ sơ Studify và yêu cầu tốt nghiệp UIT theo nguồn chính thức/web_search.",
                        "Không được chỉ trả lời số tín chỉ còn thiếu rồi dừng; phải nêu các điều kiện tốt nghiệp như hoàn thành CTĐT/tín chỉ, học phần bắt buộc hoặc khối tốt nghiệp, chuẩn ngoại ngữ, GDQP/GDTC/nghĩa vụ học phí/kỷ luật nếu nguồn có.",
                    ]
                )
        if "procedure" in topics:
            rules.extend(
                [
                    "Với câu hỏi thủ tục như giấy xác nhận, bảo lưu, tạm ngưng, trả lời theo 4 ý: làm ở đâu, cần gì, các bước, liên hệ.",
                ]
            )
        if "schedule" in topics:
            rules.extend(
                [
                    "Với câu hỏi lịch học hoặc lịch thi, nêu ngay học kỳ/đợt áp dụng, ngày cập nhật gần nhất và nơi xem chi tiết; nếu cần xác nhận ĐKHP thì nhắc rõ.",
                ]
            )
        if "annual_plan" in topics:
            rules.extend(
                [
                    "Với câu hỏi kế hoạch năm học hoặc nghỉ hè, phải nêu rõ năm học áp dụng, mốc học kỳ 2, giai đoạn thi và học kỳ hè nếu nguồn có.",
                    "Nếu trường không công bố một kỳ nghỉ hè toàn trường cố định, phải nói rõ đây là lịch khung và giải thích khoảng nghỉ thực tế theo mốc HK2 và HK hè.",
                    "Không ước lượng số tuần hoặc số tháng nghỉ hè nếu nguồn không nêu ngày bắt đầu và ngày kết thúc cụ thể.",
                    "Nếu câu hỏi hỏi về nghỉ hè năm 2026, ưu tiên bám kế hoạch năm học 2025-2026 để nêu mốc thi HK2 trong tháng 6/2026 và học kỳ hè khoảng giữa tháng 7/2026 đến tháng 8/2026 nếu ngữ cảnh có.",
                ]
            )
        if "academic_warning" in topics:
            rules.extend(
                [
                    "Với câu hỏi cảnh báo học vụ hoặc cảnh báo học tập, phải nêu đây là quy trình chính thức của UIT và giải thích ngắn gọn sinh viên cần theo dõi điều gì và xử lý ra sao.",
                ]
            )
        if "curriculum" in topics or "special_program" in topics:
            rules.extend(
                [
                    "Với câu hỏi về CTĐT, ngành học hoặc chương trình đặc biệt, nói rõ đang áp dụng cho khóa hoặc chương trình nào, rồi mới tóm tắt cấu trúc hoặc nơi tra cứu chính thức.",
                ]
            )
        if "personal_academic" in topics:
            rules.extend(
                [
                    "Đây là câu hỏi có yếu tố học vụ cá nhân. Nếu system context có hồ sơ sinh viên, hãy dùng trực tiếp GPA, tín chỉ, chương trình, môn còn thiếu hoặc tiến độ tốt nghiệp của chính sinh viên.",
                    "Không yêu cầu sinh viên nhập lại MSSV, GPA, chương trình hoặc số tín chỉ nếu dữ liệu đó đã có trong system context.",
                    "Nếu câu trả lời dựa trên dữ liệu mô phỏng hoặc dữ liệu nội bộ Studify, phải nói rõ đây chưa thay thế xác nhận chính thức từ UIT.",
                ]
            )
        if self._is_next_course_planning_query(effective_query):
            rules.extend(
                [
                    "Với câu hỏi gợi ý môn nên học tiếp theo, không trả lời chung chung theo nguyên tắc; phải đề xuất danh sách học phần cụ thể dựa trên hồ sơ sinh viên.",
                    "Trước khi chốt danh sách, phải dùng web_search để kiểm tra CTĐT, học phần tiên quyết, kế hoạch đào tạo hoặc thông tin đăng ký học phần công khai từ UIT.",
                    "Nếu dữ liệu web không khớp chính xác ngành/khóa, hãy nêu rõ giới hạn xác minh và vẫn đưa phương án thận trọng dựa trên hồ sơ Studify.",
                    "Không được bịa mã môn/tên môn khi nguồn web không cung cấp; các môn đang học chỉ là tiền đề, không phải danh sách nên đăng ký lại.",
                ]
            )
        if "leadership" in topics:
            rules.extend(
                [
                    "Mặc định các cụm 'trường', 'của trường', 'trường mình' là Trường Đại học Công nghệ Thông tin - ĐHQG-HCM (UIT) nếu người dùng không nêu trường khác rõ ràng.",
                    "Với câu hỏi về Hiệu trưởng hoặc Ban Giám hiệu UIT, phải dùng RAG tài liệu UIT và gọi web_search để kiểm tra trang Ban Giám hiệu hoặc nguồn chính thức hiện tại trước khi kết luận.",
                    "Không được đồng nhất chức danh 'Phó hiệu trưởng phụ trách' với 'Hiệu trưởng'; phải giữ nguyên chức danh đúng như nguồn chính thức ghi.",
                    "Với câu hỏi về Hiệu trưởng hoặc Ban Giám hiệu, chỉ trả lời từ nguồn Ban Giám hiệu chính thức; không lẫn sang OEP, CTĐT, phòng ban hay chương trình đặc biệt nếu người dùng không hỏi.",
                    "Nếu nguồn Ban Giám hiệu hiện không ghi chức danh Hiệu trưởng, phải nói rõ không nên khẳng định có Hiệu trưởng; nêu người đang được ghi là Phó hiệu trưởng phụ trách và Phó hiệu trưởng.",
                ]
            )
        if self._has_any(normalized, ["moi nhat", "hien tai", "nam nay", "2026", "2025", "2024"]):
            rules.append("Nếu câu hỏi mang tính cập nhật, phải ưu tiên văn bản mới nhất trong ngữ cảnh và nêu rõ ngày ban hành hoặc ngày đăng.")
        return " ".join(rules)

    def _english_requirement_brief(self, contexts: list[RetrievedContext], effective_query: str) -> str | None:
        normalized = self._normalize(effective_query)
        if not any(token in normalized for token in ["tieng anh", "ngoai ngu", "chuan dau ra", "toeic", "ielts", "vstep", "vnu ept"]):
            return None

        official_contexts = [item for item in contexts if item.document.is_official_uit]
        if not official_contexts:
            return None

        has_daa_guide = any("chuan qua trinh va chuan dau ra ngoai ngu" in self._normalize(item.document.title) for item in official_contexts)
        has_equivalence_table = any(
            any(marker in self._normalize((item.document.title or "") + " " + (item.document.url or "")) for marker in ["108 qd", "141 qd", "547 qd"])
            or any(marker in self._normalize(item.document.cleaned_content or "") for marker in ["ielts 4 5", "ielts 5 5", "ielts 6 0", "business vantage", "toefl ibt"])
            for item in official_contexts
        )
        has_oep_560 = any(
            any(marker in self._normalize((item.document.title or "") + " " + (item.document.url or "") + " " + (item.document.cleaned_content or "")) for marker in ["560 qd", "ielts academic", "ielts general"])
            for item in official_contexts
        )

        notes: list[str] = []
        notes.append("- Nếu người dùng hỏi chung mà không nêu khóa, hãy mở đầu bằng mốc đại trà khóa tuyển 2024 trở về sau như chuẩn hiện hành ưu tiên.")
        if has_daa_guide:
            notes.extend(
                [
                    "- Chương trình đại trà khóa 2024 trở về sau: hoàn thành các môn AV theo CTĐT và đạt chuẩn đầu ra TOEIC 4 kỹ năng Nghe-Đọc 450, Nói-Viết 185 hoặc chứng chỉ tương đương.",
                    "- Chương trình đại trà khóa 2022-2023: chuẩn đầu ra cũng là TOEIC 4 kỹ năng Nghe-Đọc 450, Nói-Viết 185 hoặc tương đương.",
                    "- Chương trình đại trà khóa 2019-2021: chuẩn đầu ra là TOEIC 4 kỹ năng Nghe-Đọc 450, Nói-Viết 205 hoặc tương đương.",
                    "- Chương trình tài năng / chất lượng cao: chuẩn đầu ra phổ biến trong bộ quy định là TOEIC 4 kỹ năng Nghe-Đọc 555, Nói-Viết 205 hoặc tương đương.",
                    "- Chương trình tiên tiến: chuẩn đầu ra phổ biến trong bộ quy định là TOEIC 4 kỹ năng Nghe-Đọc 675, Nói-Viết 205 hoặc tương đương.",
                ]
            )
        if has_equivalence_table:
            notes.extend(
                [
                    "- Bảng quy đổi chứng chỉ trong quy định ngoại ngữ nêu rõ: CTĐTr tương đương IELTS 4.5; CTTN/CTCLC tương đương IELTS 5.5; CTTT tương đương IELTS 6.0.",
                ]
            )
        if has_oep_560:
            notes.extend(
                [
                    "- Theo thông báo OEP về QĐ 560/QĐ-ĐHCNTT ngày 05/06/2024, khóa tuyển 2024 dùng quy định sửa đổi và trường chấp nhận cả IELTS Academic lẫn IELTS General khi xét tương đương.",
                ]
            )

        if not notes:
            return None
        return "Dùng các kết luận chính thức sau để trả lời dứt điểm, không né tránh:\n" + "\n".join(notes)

    def _topic_focus_brief(self, contexts: list[RetrievedContext], effective_query: str) -> str | None:
        topics = self._query_topics(effective_query)
        if not topics or topics == {"english"}:
            return None

        official_contexts = [item for item in contexts if item.document.is_official_uit]
        if not official_contexts:
            return None

        haystack = self._normalize(
            "\n".join(
                filter(
                    None,
                    [
                        f"{item.document.title} {item.document.url} {item.excerpt} {(item.document.summary or '')} {(item.document.cleaned_content or '')[:1800]}"
                        for item in official_contexts[:5]
                    ],
                )
            )
        )
        notes: list[str] = []

        if "registration" in topics:
            if self._has_any(haystack, ["xac nhan dkhp", "dang ky hoc phan", "dkhp uit edu vn", "student uit edu vn hocphan xacnhan dkhp"]):
                notes.append("- Trả lời phải nêu rõ bước xác nhận ĐKHP và nói đây là điều kiện để thời khóa biểu chính thức nếu nguồn có nêu.")
            if self._has_any(haystack, ["cong cu tu dong", "chiem cho", "dang ky thay", "nhan cho"]):
                notes.append("- Nhắc rõ các hành vi chiếm chỗ, đăng ký thay hoặc dùng công cụ tự động là vi phạm nếu nguồn có nêu.")
            if self._has_any(haystack, ["phongld uit edu vn", "098 988 1027"]):
                notes.append("- Nếu nguồn có email hoặc số liên hệ về mã lớp hoặc TKB, đưa luôn vào phần cuối câu trả lời.")

        if "tuition" in topics:
            if self._has_any(haystack, ["hoc phi", "thu hoc phi", "den het ngay", "thoi gian dong hoc phi"]):
                notes.append("- Với học phí, phải nêu rõ học kỳ áp dụng và hạn đóng nếu trong nguồn có ngày cụ thể.")
            if self._has_any(haystack, ["mien giam hoc phi", "gia han hoc phi", "khong phat sinh hoc phi"]):
                notes.append("- Nếu nguồn có ngoại lệ hoặc lưu ý về miễn giảm/gia hạn/không phát sinh học phí, phải nói ngắn gọn nhưng đủ.")

        if "scholarship" in topics:
            if self._has_any(haystack, ["hoc bong", "dang ky", "den het ngay", "khuyen khich hoc tap", "ngoai ngan sach"]):
                notes.append("- Với học bổng, phải nêu rõ loại học bổng, đối tượng, hạn đăng ký và link đăng ký nếu nguồn có.")
            if self._has_any(haystack, ["khong xet hoc bong", "duoi 14 tin chi", "bao hiem y te", "ky luat"]):
                notes.append("- Nếu nguồn có điều kiện loại trừ khi xét học bổng, phải liệt kê ngắn gọn các điều kiện quan trọng nhất.")

        if "graduation" in topics:
            if self._has_any(haystack, ["xet tot nghiep", "dot xet tot nghiep", "dieu kien tot nghiep", "ra truong"]):
                notes.append("- Với tốt nghiệp, phải nêu ngay đợt xét hoặc điều kiện chính trước, sau đó mới đến hướng dẫn chi tiết.")

        if "procedure" in topics:
            if self._has_any(haystack, ["giay xac nhan", "xac nhan sinh vien", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc", "chuyen nganh", "song nganh"]):
                notes.append("- Với thủ tục, phải trả lời theo bước và chỉ rõ nơi thực hiện thay vì mô tả chung chung.")

        if "schedule" in topics:
            if self._has_any(haystack, ["thoi khoa bieu", "lich thi", "cap nhat ngay", "giua ky", "cuoi ky", "dkhp", "dang ky hoc phan"]):
                notes.append("- Với lịch học/lịch thi, phải nêu học kỳ hoặc đợt áp dụng, ngày cập nhật và nơi xem chi tiết.")

        if "annual_plan" in topics:
            if self._has_any(haystack, ["ke hoach dao tao nam hoc", "khai giang", "tet am lich", "hk he", "ve he", "nghi he"]):
                notes.append("- Với kế hoạch năm học hoặc nghỉ hè, phải trả lời theo mốc thời gian thật trong kế hoạch năm học, không phỏng đoán theo thông lệ.")
            if self._has_any(haystack, ["lich khung", "hoc ky he", "hk he"]):
                notes.append("- Nếu nguồn chỉ là lịch khung, phải nói rõ khoảng nghỉ thực tế còn phụ thuộc học hè, GDQP&AN hoặc lớp đặc thù.")

        if "academic_warning" in topics:
            if self._has_any(haystack, ["canh bao sinh vien", "canh bao hoc vu", "canh bao hoc tap", "xu ly hoc vu", "ket qua dang ky hoc phan", "ket qua hoc tap"]):
                notes.append("- Với cảnh báo học vụ, phải nêu đây là quy trình chính thức của UIT và gắn nó với kết quả ĐKHP hoặc kết quả học tập chứ không nói chung chung.")

        if "curriculum" in topics or "special_program" in topics:
            if self._has_any(haystack, ["chuong trinh dao tao", "ctdt", "ctdt khoa", "tai nang", "chat luong cao", "tien tien", "oep"]):
                notes.append("- Với CTĐT hoặc chương trình đặc biệt, phải nêu rõ chương trình/khóa áp dụng trước rồi mới tóm tắt môn học hoặc quy định.")

        if not notes:
            return None
        return "Dùng các ưu tiên trình bày sau để trả lời đầy đủ hơn:\n" + "\n".join(notes)

    def _context_limit(self, analysis: QueryAnalysis, effective_query: str, chat_mode: str = "quick") -> int:
        topics = self._query_topics(effective_query)
        if "leadership" in topics:
            base_limit = 4
        elif analysis.category == "ACADEMIC":
            base_limit = 8 if topics else 6
        elif analysis.category == "ANNOUNCEMENT":
            base_limit = 6 if topics.intersection({"schedule", "scholarship", "tuition", "graduation", "registration", "annual_plan", "academic_warning"}) else 4
        else:
            base_limit = 4
        return base_limit if chat_mode == "extended" else min(base_limit, 4)

    def _normalize_chat_mode(self, chat_mode: str) -> str:
        return "extended" if chat_mode == "extended" else "quick"

    def _chat_mode_guidance(self, chat_mode: str) -> str:
        shared = (
            "Trước mọi câu trả lời, hãy suy nghĩ ngầm theo mức độ khó của câu hỏi: "
            "xác định người dùng thật sự cần gì, dữ liệu nào đã có trong hồ sơ/ngữ cảnh, điểm nào có thể gây hiểu sai, "
            "rồi mới trả lời. Không in ra chuỗi suy luận nội bộ; chỉ thể hiện kết luận, lý do ngắn và bước tiếp theo nếu hữu ích. "
            "Câu dễ thì suy nghĩ rất nhanh và trả lời trong vài câu. Câu học vụ, cá nhân, kế hoạch, hoặc câu có rủi ro sai thì phân tích kỹ hơn, "
            "so sánh mốc áp dụng, nêu giả định và nhắc nguồn/xác nhận chính thức khi cần."
        )
        if chat_mode == "extended":
            return (
                f"{shared} "
                "Chế độ mở rộng: được phép dùng web_search khi cần kiểm tra thông tin mới hoặc khi RAG chưa đủ chắc. "
                "Trả lời đầy đủ hơn, có thể chia thành kết luận, phân tích và việc nên làm, nhưng vẫn ưu tiên nguồn UIT chính thức và không bịa nguồn."
            )
        return (
            f"{shared} "
            "Chế độ nhanh: ưu tiên trả lời ngắn gọn bằng dữ liệu UIT đã có trong hệ thống và lịch sử chat. "
            "Với câu đơn giản, trả lời trực tiếp trong 1-3 câu. Với câu cần đánh giá, thêm 1-2 lý do ngắn thay vì chỉ đọc dữ liệu. "
            "Chỉ dùng web_search khi dữ liệu hiện có không đủ hoặc có khả năng đã cũ; nếu dùng thì tìm ít kết quả, truy vấn ngắn, rồi tổng hợp nhanh."
        )

    def _stream_text_chunks(self, content: str, words_per_chunk: int = 18) -> list[str]:
        words = content.split(" ")
        if len(words) <= words_per_chunk:
            return [content]

        chunks: list[str] = []
        current_words: list[str] = []
        for word in words:
            current_words.append(word)
            if len(current_words) >= words_per_chunk:
                chunks.append(" ".join(current_words).strip())
                current_words = []
        if current_words:
            chunks.append(" ".join(current_words).strip())
        return [chunk if index == 0 else f" {chunk}" for index, chunk in enumerate(chunks) if chunk]

    def _context_haystack(self, context: RetrievedContext) -> str:
        return self._normalize(
            " ".join(
                filter(
                    None,
                    [
                        context.document.title,
                        context.document.url,
                        context.document.summary or "",
                        context.document.cleaned_content or "",
                        context.excerpt,
                    ],
                )
            )
        )

    def _leadership_context_haystack(self, context: RetrievedContext) -> str:
        return self._normalize(
            " ".join(
                filter(
                    None,
                    [
                        context.document.title,
                        context.document.url,
                        context.document.summary or "",
                        context.excerpt,
                    ],
                )
            )
        )

    def _focused_contexts(self, contexts: list[RetrievedContext], effective_query: str) -> list[RetrievedContext]:
        topics = self._query_topics(effective_query)
        if "leadership" not in topics:
            return contexts

        leadership_contexts = [
            item
            for item in contexts
            if item.document.is_official_uit
            and self._has_any(
                self._leadership_context_haystack(item),
                ["ban giam hieu", "pho hieu truong phu trach", "nguyen tan tran minh khang", "nguyen luu thuy ngan"],
            )
        ]
        return leadership_contexts[:3] if leadership_contexts else contexts[:1]

    def _leadership_grounding_brief(self, contexts: list[RetrievedContext], effective_query: str) -> str | None:
        if not self._is_default_uit_school_context_query(effective_query):
            return None

        official_contexts = [
            item
            for item in contexts
            if item.document.is_official_uit
            and self._has_any(
                self._leadership_context_haystack(item),
                ["ban giam hieu", "pho hieu truong phu trach", "nguyen tan tran minh khang", "nguyen luu thuy ngan"],
            )
        ]
        if not official_contexts:
            return None

        combined = " ".join(self._context_haystack(item) for item in official_contexts)
        notes = [
            "Ràng buộc dữ kiện Ban Giám hiệu UIT: đọc đúng chức danh trong nguồn chính thức, không suy diễn chức danh cao hơn.",
            "Không được đồng nhất 'Phó hiệu trưởng phụ trách' với 'Hiệu trưởng'.",
            "Nếu nguồn chỉ ghi 'Phó hiệu trưởng phụ trách' hoặc không có dòng chức danh 'Hiệu trưởng', câu đầu phải nói rõ trang Ban Giám hiệu UIT hiện không ghi chức danh Hiệu trưởng.",
            "Chỉ được gọi một người là Hiệu trưởng nếu web_search tìm được nguồn UIT chính thức mới hơn ghi rõ chức danh của người đó là 'Hiệu trưởng'.",
        ]
        if "pho hieu truong phu trach" in combined and "nguyen tan tran minh khang" in combined:
            notes.append("Theo RAG hiện có, PGS.TS. Nguyễn Tấn Trần Minh Khang đang được ghi là Phó hiệu trưởng phụ trách, không phải dòng chức danh Hiệu trưởng.")
        if "nguyen luu thuy ngan" in combined:
            notes.append("Theo RAG hiện có, PGS.TS. Nguyễn Lưu Thùy Ngân đang được ghi là Phó hiệu trưởng.")
        return "\n".join(notes)

    async def _deterministic_uit_leadership_answer(self, prepared: PreparedTurn) -> str | None:
        if not self._is_default_uit_school_context_query(prepared.effective_query):
            return None

        query = "site:uit.edu.vn/bai-viet/ban-giam-hieu Ban Giám hiệu UIT Hiệu trưởng"
        web_text = ""
        try:
            from app.services.web_search_service import WebSearchService

            web_text = await WebSearchService().search(query, max_results=2)
        except Exception as exc:
            logger.warning("[chat] web_search Ban Giám hiệu UIT thất bại: %s", exc)

        source_text = " ".join(
            filter(
                None,
                [
                    *[
                        " ".join(
                            filter(
                                None,
                                [
                                    item.document.title,
                                    item.document.url,
                                    item.document.summary or "",
                                    item.document.cleaned_content or "",
                                    item.excerpt,
                                ],
                            )
                        )
                        for item in prepared.contexts
                    ],
                    web_text,
                ],
            )
        )
        normalized = self._normalize(source_text)
        if "ban giam hieu" not in normalized and "nguyen tan tran minh khang" not in normalized:
            return None

        source_url = "https://www.uit.edu.vn/bai-viet/ban-giam-hieu"
        has_khang = "nguyen tan tran minh khang" in normalized
        has_ngan = "nguyen luu thuy ngan" in normalized
        khang_is_vice_in_charge = has_khang and "pho hieu truong phu trach" in normalized

        if khang_is_vice_in_charge:
            answer = (
                "Trang **Ban Giám hiệu UIT** hiện không ghi chức danh **Hiệu trưởng**. "
                "Nguồn chính thức đang ghi **PGS.TS. Nguyễn Tấn Trần Minh Khang** là "
                "**Phó hiệu trưởng phụ trách**."
            )
            if has_ngan:
                answer += "\n\n### Chi tiết\n- **PGS.TS. Nguyễn Tấn Trần Minh Khang**: Phó hiệu trưởng phụ trách.\n- **PGS.TS. Nguyễn Lưu Thùy Ngân**: Phó hiệu trưởng."
            answer += f"\n\n### Nguồn tham khảo\n- Trang Ban Giám hiệu UIT: {source_url}"
            return answer

        if has_khang and "hieu truong" in normalized and "pho hieu truong" not in normalized:
            return (
                "Theo trang **Ban Giám hiệu UIT**, **PGS.TS. Nguyễn Tấn Trần Minh Khang** "
                f"đang được ghi là **Hiệu trưởng**.\n\n### Nguồn tham khảo\n- Trang Ban Giám hiệu UIT: {source_url}"
            )

        return None

    def _compact_fact(self, text: str, limit: int = 320) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    def _grounding_contexts(self, contexts: list[RetrievedContext], effective_query: str) -> list[RetrievedContext]:
        topics = self._query_topics(effective_query)
        normalized = self._normalize(effective_query)
        current_year = str(datetime.now(timezone.utc).year)

        official_contexts = [item for item in contexts if item.document.is_official_uit]
        if not official_contexts:
            return contexts[:3]

        scored: list[tuple[float, RetrievedContext]] = []
        for item in official_contexts:
            haystack = self._context_haystack(item)
            score = item.score

            if "annual_plan" in topics:
                if self._has_any(haystack, ["ke hoach dao tao nam hoc", "ke hoach nam", "nghi he", "hoc ky he", "khai giang"]):
                    score += 1.8
                if "2026" in normalized and self._has_any(haystack, ["2025 2026"]):
                    score += 0.8
                if "2027" in normalized and self._has_any(haystack, ["2026 2027"]):
                    score += 0.8
                if "2026" not in normalized and "2027" not in normalized and current_year == "2026" and self._has_any(haystack, ["2025 2026"]):
                    score += 0.35

            if "tuition" in topics:
                if self._has_any(haystack, ["thu hoc phi", "quy dinh muc thu hoc phi", "hoc phi"]):
                    score += 1.8
                if "khtc uit edu vn" in haystack or "khtc.uit.edu.vn" in (item.document.url or ""):
                    score += 0.8

            if "registration" in topics and self._has_any(haystack, ["dang ky hoc phan", "dkhp", "xac nhan dkhp"]):
                score += 1.4

            if "graduation" in topics and self._has_any(haystack, ["xet tot nghiep", "tot nghiep", "dieu kien tot nghiep"]):
                score += 1.4

            if "procedure" in topics and self._has_any(haystack, ["giay xac nhan", "giay gioi thieu", "thu tuc", "bao luu", "tam ngung", "thoi hoc"]):
                score += 1.4

            if "english" in topics and self._has_any(haystack, ["ngoai ngu", "tieng anh", "toeic", "ielts", "vnu ept", "vstep", "chuan dau ra"]):
                score += 1.4

            scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected: list[RetrievedContext] = []
        seen_ids: set[int] = set()
        for _, item in scored:
            if item.document.id in seen_ids:
                continue
            seen_ids.add(item.document.id)
            selected.append(item)
            if len(selected) >= 3:
                break
        return selected

    def _grounding_brief(self, contexts: list[RetrievedContext], effective_query: str) -> str | None:
        selected = self._grounding_contexts(contexts, effective_query)
        if not selected:
            return None

        topics = self._query_topics(effective_query)
        lines = ["Dữ kiện UIT cần bám sát khi trả lời:"]

        for item in selected:
            fact = self._compact_fact(item.document.summary or item.excerpt or item.document.cleaned_content or "")
            if not fact:
                continue
            lines.append(f"- {item.document.title}: {fact}")

        if len(lines) == 1:
            return None

        lines.append("- Chỉ kết luận từ các dữ kiện UIT ở trên và phần trích đoạn nguồn đi kèm.")
        lines.append("- Nếu dữ kiện chưa đủ để kết luận chắc chắn, hãy nói rõ phần nào chưa đủ thay vì suy diễn thêm.")

        if "annual_plan" in topics:
            lines.append("- Với lịch năm học, phải phân biệt lịch khung năm học với lịch nghỉ cố định của toàn trường.")
        if "tuition" in topics:
            lines.append("- Với học phí, tách rõ hạn đóng, mức thu, chương trình và khóa áp dụng; không gộp chúng thành một ý.")
        if "registration" in topics:
            lines.append("- Với đăng ký học phần, nêu rõ bước xác nhận, mốc thời gian và hệ quả nếu quá hạn.")
        if "graduation" in topics:
            lines.append("- Với tốt nghiệp, nêu đợt xét hoặc điều kiện chính trước rồi mới nói đến chi tiết.")

        return "\n".join(lines)

    def _facts_brief(self, facts: list[StructuredKnowledgeFact]) -> str | None:
        if not facts:
            return None

        lines = ["Dữ kiện cấu trúc đã chuẩn hóa từ corpus UIT:"]
        for fact in facts[:5]:
            qualifiers: list[str] = []
            if fact.school_year:
                qualifiers.append(f"năm học {fact.school_year}")
            if fact.applies_to_programs:
                qualifiers.append("chương trình: " + ", ".join(fact.applies_to_programs[:3]))
            if fact.applies_to_cohorts:
                qualifiers.append("khóa: " + ", ".join(fact.applies_to_cohorts[:4]))
            qualifier_text = f" ({'; '.join(qualifiers)})" if qualifiers else ""
            lines.append(f"- [{self._fact_type_value(fact.fact_type)}] {fact.title}{qualifier_text}: {fact.fact_text}")
        lines.append("- Ưu tiên các dữ kiện cấu trúc này khi chúng phù hợp trực tiếp với câu hỏi.")
        return "\n".join(lines)

    def _assistant_reply(
        self,
        session_id: int,
        analysis: QueryAnalysis,
        citations: list[CitationItem],
        suggestions: list[str],
        answer: str,
    ) -> ChatReply:
        return ChatReply(
            session_id=session_id,
            category=analysis.category,
            answer=answer,
            is_urgent=analysis.is_urgent,
            risk_score=analysis.risk_score,
            citations=citations,
            action_suggestions=suggestions,
        )

    def _save_assistant_message(
        self,
        db: Session,
        session: ChatSession,
        analysis: QueryAnalysis,
        answer: str,
    ) -> None:
        session.updated_at = datetime.now(timezone.utc)
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                category=analysis.category,
                content=answer,
                risk_score=analysis.risk_score,
                is_urgent=analysis.is_urgent,
            )
        )
        db.commit()

    def _save_user_message(
        self,
        db: Session,
        session: ChatSession,
        analysis: QueryAnalysis,
        content: str,
    ) -> None:
        session.updated_at = datetime.now(timezone.utc)
        db.add(
            ChatMessage(
                session_id=session.id,
                role="user",
                category=analysis.category,
                content=content,
                risk_score=analysis.risk_score,
                is_urgent=analysis.is_urgent,
            )
        )
        db.commit()

    async def _prepare_turn(
        self,
        db: Session,
        session: ChatSession,
        content: str,
        user: User | None = None,
        analysis: QueryAnalysis | None = None,
        chat_mode: str = "quick",
    ) -> PreparedTurn:
        chat_mode = self._normalize_chat_mode(chat_mode)
        raw_effective_query = self._build_effective_query(db, session, content)
        effective_query = self.query_rewriter.rewrite(raw_effective_query)
        # Phân loại ý định/khủng hoảng trên query TRƯỚC khi mở rộng (rewrite).
        # Rewriter nối thêm từ khoá học vụ để tăng recall retrieval; nếu phân
        # loại trên chuỗi đã mở rộng sẽ bị lệch sang ACADEMIC và có thể xoá mất
        # tín hiệu khủng hoảng.
        analysis = self._route_analysis(raw_effective_query, effective_query, analysis or analyze_query(raw_effective_query))
        contexts: list[RetrievedContext] = []
        facts: list[StructuredKnowledgeFact] = []
        if self._should_use_retrieval(analysis, effective_query):
            contexts = await self.rag.retrieve(db, effective_query, limit=self._context_limit(analysis, effective_query, chat_mode))
            contexts = self._focused_contexts(contexts, effective_query)
            if analysis.category == "WELLBEING":
                contexts = [item for item in contexts if item.document.is_wellbeing_related][:3]
            fact_matches = self.facts.search_facts(
                db,
                effective_query,
                context_document_ids=[item.document.id for item in contexts],
                limit=5,
            )
            facts = [item.fact for item in fact_matches]
        citations = [
            CitationItem(
                document_id=item.document.id,
                title=item.document.title,
                url=item.document.url,
                source_label="Nguồn UIT chính thức" if item.document.is_official_uit else "Nguồn tham khảo",
                confidence=item.document.confidence_level.value if hasattr(item.document.confidence_level, "value") else str(item.document.confidence_level),
                excerpt=item.excerpt,
                updated_at=item.document.updated_source_at,
            )
            for item in contexts
        ]

        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.asc())
            .limit(12)
            .all()
        )

        system_prompt = self._system_prompt(
            db,
            "chat_system_prompt",
            (
                "Bạn là Studify, trợ lý đồng hành dành cho sinh viên UIT. "
                "Tính cách của bạn: ấm áp, gần gũi, kiên nhẫn và LUÔN SẴN SÀNG LẮNG NGHE, TÂM SỰ "
                "như một người bạn cùng trường — không phán xét, không vội vàng. Khi người dùng muốn "
                "trò chuyện hoặc chia sẻ cảm xúc, hãy chủ động đồng hành, hỏi han nhẹ nhàng và ở lại "
                "với cảm xúc của họ trước, rồi mới gợi ý nhẹ nếu phù hợp. "
                "Luôn trả lời bằng tiếng Việt tự nhiên, ngắn gọn, hữu ích. "
                "Ưu tiên thông tin chính thức từ UIT, không bịa nguồn, và nếu dữ liệu có thể cũ thì phải nói rõ. "
                "Chatbot này không có mode cố định; bạn phải tự nhận diện khi nào người dùng đang hỏi học vụ, thông báo, lên kế hoạch hay chỉ đang cần một lời đồng hành nhẹ. "
                "Ở các đoạn tâm sự, chỉ hỗ trợ ở mức đồng hành nhẹ, lắng nghe, gợi ý nghỉ ngắn, sắp xếp lại việc và khuyến khích tìm người hỗ trợ trong trường khi cần. "
                "Với câu hỏi học vụ phổ biến, phải trả lời trực tiếp, đầy đủ, chắc chắn theo nguồn chính thức trước; không hỏi lại người dùng nếu không thật sự bắt buộc."
            ),
        )
        context_block = "\n\n".join(
            f"[Nguồn {index + 1}] {item.document.title}\nURL: {item.document.url}\nTrích đoạn: {item.excerpt}"
            for index, item in enumerate(contexts)
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "system", "content": self._chat_mode_guidance(chat_mode)})
        messages.append({"role": "system", "content": self._category_guidance(analysis.category)})
        messages.append({"role": "system", "content": self._direct_answer_rules(effective_query)})
        if not self._is_quick_no_web_query(effective_query):
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Chính sách web_search hiện tại: với mọi câu hỏi không phải chào hỏi hoặc hỏi đáp nhanh, "
                        "hãy gọi web_search trước khi kết luận. Ưu tiên truy vấn ngắn, dùng Google web_search, "
                        "query đầu tiên phải ưu tiên daa.uit.edu.vn, oep.uit.edu.vn, ctsv.uit.edu.vn; "
                        "chỉ mở rộng sang student.uit.edu.vn, courses.uit.edu.vn hoặc uit.edu.vn nếu 3 site ưu tiên chưa đủ dữ liệu. "
                        "Nếu web_search không tìm thấy, hãy trả lời trực tiếp bằng kiến thức GPT hiện có và nói rõ chưa xác minh được bằng web; "
                        "không kết thúc bằng yêu cầu người dùng gửi link trừ khi câu hỏi thật sự không thể hiểu được."
                    ),
                }
            )
        user_brief = self._user_context_brief(db, user) if user else None
        if user_brief:
            messages.append({"role": "system", "content": user_brief})
        course_planning_brief = self._course_planning_brief(user, effective_query)
        if course_planning_brief:
            messages.append({"role": "system", "content": course_planning_brief})
        graduation_personal_brief = self._graduation_personal_brief(user, effective_query)
        if graduation_personal_brief:
            messages.append({"role": "system", "content": graduation_personal_brief})
        if effective_query.strip() != content.strip():
            messages.append(
                {
                    "role": "system",
                    "content": f"Câu hỏi hiện tại đang nối tiếp ngữ cảnh hội thoại trước đó. Hãy hiểu câu hỏi đầy đủ là: {effective_query}",
                }
            )
        if context_block:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Sử dụng ngữ cảnh dưới đây để trả lời. "
                        "Nếu trích nguồn không chính thức UIT thì phải nói rõ đó là nguồn tham khảo.\n\n"
                        f"{context_block}"
                    ),
                }
            )
        english_brief = self._english_requirement_brief(contexts, effective_query)
        if english_brief:
            messages.append({"role": "system", "content": english_brief})
        topic_focus_brief = self._topic_focus_brief(contexts, effective_query)
        if topic_focus_brief:
            messages.append({"role": "system", "content": topic_focus_brief})
        leadership_grounding_brief = self._leadership_grounding_brief(contexts, effective_query)
        if leadership_grounding_brief:
            messages.append({"role": "system", "content": leadership_grounding_brief})
        grounding_brief = self._grounding_brief(contexts, effective_query)
        if grounding_brief:
            messages.append({"role": "system", "content": grounding_brief})
        facts_brief = self._facts_brief(facts)
        if facts_brief:
            messages.append({"role": "system", "content": facts_brief})
        if analysis.category in {"ACADEMIC", "ANNOUNCEMENT"}:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Quy trình trả lời học vụ: ưu tiên dùng dữ liệu UIT trong ngữ cảnh phía trên nếu nó "
                        "đã đủ và ĐÚNG trọng tâm câu hỏi (đúng ngành, đúng đối tượng, đúng khóa). "
                        "Nếu ngữ cảnh KHÔNG có hoặc KHÔNG khớp (ví dụ người dùng hỏi một ngành/chủ đề mà ngữ cảnh "
                        "chỉ chứa ngành khác), hãy gọi công cụ web_search để tra cứu trên các trang chính thức của UIT "
                        "theo thứ tự ưu tiên daa.uit.edu.vn, oep.uit.edu.vn, ctsv.uit.edu.vn trước, rồi student.uit.edu.vn, courses.uit.edu.vn, uit.edu.vn. "
                        "Tuyệt đối không bịa nguồn; nếu sau khi tìm vẫn không có nguồn chính thức thì dùng kiến thức GPT/hồ sơ Studify để trả lời phần có thể, "
                        "nói rõ phần đó chưa xác minh được bằng web search."
                    ),
                }
            )
        for message in history:
            messages.append({"role": "assistant" if message.role == "assistant" else "user", "content": message.content})

        return PreparedTurn(
            analysis=analysis,
            effective_query=effective_query,
            contexts=contexts,
            facts=facts,
            citations=citations,
            suggestions=self._action_suggestions(analysis.category),
            messages=messages,
        )

    async def answer(self, db: Session, session: ChatSession, content: str, chat_mode: str = "quick", user: User | None = None) -> ChatReply:
        chat_mode = self._normalize_chat_mode(chat_mode)
        raw_effective_query = self._build_effective_query(db, session, content)
        effective_query = self.query_rewriter.rewrite(raw_effective_query)
        # Phân loại trên query trước rewrite để không bị nhiễu từ khoá học vụ.
        analysis = self._route_analysis(raw_effective_query, effective_query, analyze_query(raw_effective_query))
        self._save_user_message(db, session, analysis, content)
        if self._is_crisis_turn(analysis):
            answer = self._crisis_answer()
            self._save_assistant_message(db, session, analysis, answer)
            return self._assistant_reply(session.id, analysis, [], self._crisis_action_suggestions(), answer)

        if self._is_general_direct_turn(analysis, effective_query):
            needs_web_search = self._general_direct_needs_web_search(effective_query)
            try:
                messages = self._general_direct_messages(db, session, content, needs_web_search=needs_web_search)
                if needs_web_search:
                    plan = await self._plan_web_search(effective_query, analysis, max_queries=3 if chat_mode == "quick" else 5)
                    search_results = await self._execute_search_plan(plan, max_results=3 if chat_mode == "quick" else 5)
                    messages = self._messages_with_search_results(messages, effective_query, plan, search_results)
                answer = await self.llm.chat(
                    messages,
                    web_search_enabled=False,
                )
            except Exception as exc:
                logger.error("[chat] direct GPT cho câu ngoài lề thất bại: %s", exc)
                answer = self._general_direct_fallback(effective_query)
            answer = answer.strip() or self._general_direct_fallback(effective_query)
            self._save_assistant_message(db, session, analysis, answer)
            return self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), answer)

        direct_time_answer = self._current_time_answer(effective_query)
        if direct_time_answer:
            self._save_assistant_message(db, session, analysis, direct_time_answer)
            return self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), direct_time_answer)

        personal_answer = self._personal_academic_answer(db, user, effective_query)
        if personal_answer and self._should_fast_personal_academic_answer(effective_query):
            self._save_assistant_message(db, session, analysis, personal_answer)
            return self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), personal_answer)

        prepared = await self._prepare_turn(db, session, content, user, analysis, chat_mode)
        deterministic_answer = await self._deterministic_uit_leadership_answer(prepared)
        if deterministic_answer:
            self._save_assistant_message(db, session, prepared.analysis, deterministic_answer)
            return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, deterministic_answer)
        if self._should_low_confidence_refuse(prepared) and not self._should_enable_web_search(prepared):
            answer = self._low_confidence_answer()
            self._save_assistant_message(db, session, prepared.analysis, answer)
            return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)
        try:
            messages = prepared.messages
            if self._should_enable_web_search(prepared) and not self._is_quick_no_web_query(prepared.effective_query):
                plan = await self._plan_web_search(prepared.effective_query, prepared.analysis, max_queries=2 if chat_mode == "quick" else 5)
                search_results = await self._execute_search_plan(plan, max_results=2 if chat_mode == "quick" else 5)
                messages = self._messages_with_search_results(messages, prepared.effective_query, plan, search_results)
            answer = await self.llm.chat(
                messages,
                web_search_enabled=False,
            )
        except Exception as exc:
            logger.error("[chat] llm chat thất bại: %s", exc)
            answer = self._fallback_answer(prepared.analysis.category, prepared.contexts)

        validation = self.citation_validator.clean_answer(answer, prepared.citations)
        self._save_assistant_message(db, session, prepared.analysis, validation.answer)
        return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, validation.answer)

    async def stream_answer(self, db: Session, session: ChatSession, content: str, chat_mode: str = "quick", user: User | None = None) -> AsyncIterator[dict]:
        chat_mode = self._normalize_chat_mode(chat_mode)
        raw_effective_query = self._build_effective_query(db, session, content)
        effective_query = self.query_rewriter.rewrite(raw_effective_query)
        # Phân loại trên query trước rewrite để không bị nhiễu từ khoá học vụ.
        analysis = self._route_analysis(raw_effective_query, effective_query, analyze_query(raw_effective_query))
        is_crisis = self._is_crisis_turn(analysis)
        yield {
            "type": "meta",
            "session_id": session.id,
            "category": analysis.category,
            "is_urgent": analysis.is_urgent,
            "risk_score": analysis.risk_score,
            "citations": [],
            "action_suggestions": self._crisis_action_suggestions() if is_crisis else self._action_suggestions(analysis.category),
        }
        await asyncio.sleep(0)
        yield {"type": "status", "label": "Studify đang ưu tiên an toàn..." if is_crisis else "Studify đang phân tích nhanh câu hỏi..."}
        await asyncio.sleep(0)
        self._save_user_message(db, session, analysis, content)
        if is_crisis:
            answer = self._crisis_answer()
            for chunk in self._stream_text_chunks(answer):
                yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, analysis, answer)
            reply = self._assistant_reply(session.id, analysis, [], self._crisis_action_suggestions(), answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        if self._is_general_direct_turn(analysis, effective_query):
            needs_web_search = self._general_direct_needs_web_search(effective_query)
            yield {
                "type": "status",
                "label": "Studify đang lập kế hoạch tìm kiếm..." if needs_web_search else "Studify đang suy nghĩ...",
            }
            answer_parts: list[str] = []
            try:
                messages = self._general_direct_messages(db, session, content, needs_web_search=needs_web_search)
                if needs_web_search:
                    plan = await self._plan_web_search(effective_query, analysis, max_queries=3 if chat_mode == "quick" else 5)
                    if plan.queries:
                        yield {"type": "status", "label": f"Đang tìm trên web theo kế hoạch: {plan.queries[0][:80]}"}
                    search_results = await self._execute_search_plan(plan, max_results=3 if chat_mode == "quick" else 5)
                    messages = self._messages_with_search_results(messages, effective_query, plan, search_results)
                    yield {"type": "status", "label": "Studify đang tổng hợp kết quả tìm kiếm..."}
                async for chunk in self.llm.stream_chat(
                    messages,
                    web_search_enabled=False,
                ):
                    if chunk.startswith(TOOL_STATUS_PREFIX):
                        yield {"type": "status", "label": chunk[len(TOOL_STATUS_PREFIX):]}
                        continue
                    deltas = self._stream_text_chunks(chunk, words_per_chunk=14) if len(chunk.split()) > 18 else [chunk]
                    for delta in deltas:
                        answer_parts.append(delta)
                        yield {"type": "chunk", "delta": delta}
            except Exception as exc:
                logger.error("[chat] direct GPT stream cho câu ngoài lề thất bại: %s", exc)

            answer = "".join(answer_parts).strip()
            if not answer:
                answer = self._general_direct_fallback(effective_query)
                for chunk in self._stream_text_chunks(answer):
                    yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, analysis, answer)
            reply = self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        direct_time_answer = self._current_time_answer(effective_query)
        if direct_time_answer:
            yield {"type": "status", "label": "Studify đang xem giờ hiện tại..."}
            for chunk in self._stream_text_chunks(direct_time_answer):
                yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, analysis, direct_time_answer)
            reply = self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), direct_time_answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        personal_answer = self._personal_academic_answer(db, user, effective_query)
        if personal_answer and self._should_fast_personal_academic_answer(effective_query):
            yield {"type": "status", "label": "Studify đang đọc hồ sơ và đánh giá ngắn..."}
            for chunk in self._stream_text_chunks(personal_answer):
                yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, analysis, personal_answer)
            reply = self._assistant_reply(session.id, analysis, [], self._action_suggestions(analysis.category), personal_answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        if chat_mode == "extended":
            yield {"type": "status", "label": "Studify đang suy nghĩ kỹ, tìm dữ liệu UIT và có thể kiểm tra web sâu..."}
        else:
            yield {"type": "status", "label": "Studify đang suy nghĩ nhanh..."}
        prepared = await self._prepare_turn(db, session, content, user, analysis, chat_mode)
        await asyncio.sleep(0)
        if self._is_default_uit_school_context_query(prepared.effective_query):
            yield {
                "type": "status",
                "label": "Đang tìm trên web: site:uit.edu.vn/bai-viet/ban-giam-hieu Ban Giám hiệu UIT Hiệu trưởng",
            }
            deterministic_answer = await self._deterministic_uit_leadership_answer(prepared)
            if deterministic_answer:
                for chunk in self._stream_text_chunks(deterministic_answer):
                    yield {"type": "chunk", "delta": chunk}
                self._save_assistant_message(db, session, prepared.analysis, deterministic_answer)
                reply = self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, deterministic_answer)
                yield {"type": "done", **reply.model_dump(mode="json")}
                return
        if self._should_low_confidence_refuse(prepared) and not self._should_enable_web_search(prepared):
            answer = self._low_confidence_answer()
            for chunk in self._stream_text_chunks(answer):
                yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, prepared.analysis, answer)
            reply = self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        messages = prepared.messages
        if self._should_enable_web_search(prepared) and not self._is_quick_no_web_query(prepared.effective_query):
            yield {"type": "status", "label": "Studify đang lập kế hoạch tìm kiếm..."}
            plan = await self._plan_web_search(prepared.effective_query, prepared.analysis, max_queries=2 if chat_mode == "quick" else 5)
            if plan.queries:
                yield {"type": "status", "label": f"Đang tìm trên web theo kế hoạch: {plan.queries[0][:80]}"}
            search_results = await self._execute_search_plan(plan, max_results=2 if chat_mode == "quick" else 5)
            messages = self._messages_with_search_results(messages, prepared.effective_query, plan, search_results)

        yield {"type": "status", "label": "Studify đang tổng hợp câu trả lời..."}

        answer_parts: list[str] = []
        try:
            async for chunk in self.llm.stream_chat(
                messages,
                web_search_enabled=False,
            ):
                # Tool status sentinel từ MimoProvider → chuyển thành status event
                if chunk.startswith(TOOL_STATUS_PREFIX):
                    yield {"type": "status", "label": chunk[len(TOOL_STATUS_PREFIX):]}
                    continue
                deltas = self._stream_text_chunks(chunk, words_per_chunk=14) if len(chunk.split()) > 18 else [chunk]
                for delta in deltas:
                    answer_parts.append(delta)
                    yield {"type": "chunk", "delta": delta}
        except Exception as exc:
            logger.error("[chat] llm stream thất bại: %s", exc)
            if not answer_parts:
                fallback = self._fallback_answer(prepared.analysis.category, prepared.contexts)
                for chunk in self._stream_text_chunks(fallback):
                    answer_parts.append(chunk)
                    yield {"type": "chunk", "delta": chunk}

        answer = "".join(answer_parts).strip()
        # Strip XML tool_call artifacts (closed tags, then any unclosed opening tag, then orphaned closing tags)
        answer = re.sub(r"<\s*tool_call\s*>.*?</\s*tool_call\s*>", "", answer, flags=re.DOTALL | re.IGNORECASE).strip()
        answer = re.sub(r"<\s*tool_call\s*>.*$", "", answer, flags=re.DOTALL | re.IGNORECASE).strip()
        answer = re.sub(r"</\s*tool_call\s*>", "", answer, flags=re.IGNORECASE).strip()
        if not answer:
            fallback = self._fallback_answer(prepared.analysis.category, prepared.contexts)
            for chunk in self._stream_text_chunks(fallback):
                answer_parts.append(chunk)
                yield {"type": "chunk", "delta": chunk}
            answer = "".join(answer_parts).strip()

        validation = self.citation_validator.clean_answer(answer, prepared.citations)
        self._save_assistant_message(db, session, prepared.analysis, validation.answer)
        reply = self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, validation.answer)
        yield {"type": "done", **reply.model_dump(mode="json")}
