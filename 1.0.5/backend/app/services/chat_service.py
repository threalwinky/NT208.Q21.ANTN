from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import StructuredKnowledgeFact
from app.models.wellbeing import SystemConfig
from app.schemas.chat import ChatReply, CitationItem
from app.services.citation_validator import CitationValidator
from app.services.llm import get_llm_provider
from app.services.llm.mimo_provider import TOOL_STATUS_PREFIX
from app.services.query_classifier import QueryAnalysis, analyze_query
from app.services.query_rewriter import QueryRewriter
from app.services.rag_service import RagService, RetrievedContext

logger = logging.getLogger(__name__)
from app.services.structured_facts_service import StructuredFactsService


@dataclass
class PreparedTurn:
    analysis: QueryAnalysis
    effective_query: str
    contexts: list[RetrievedContext]
    facts: list[StructuredKnowledgeFact]
    citations: list[CitationItem]
    suggestions: list[str]
    messages: list[dict[str, str]]


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
        if self._has_any(normalized, ["ctdt", "chuong trinh dao tao", "ke hoach hoc tap", "khung chuong trinh", "hoc mon nao", "nganh hoc"]):
            topics.add("curriculum")
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
                "Người dùng đang cần một giọng điệu đồng hành nhẹ. "
                "Hãy phản hồi ấm áp, tự nhiên, không lên lớp, không chẩn đoán. "
                "Ưu tiên lắng nghe, tóm lại ngắn điều người dùng đang vướng, rồi gợi ý 2-3 bước nhỏ có thể làm ngay."
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
        if self._is_crisis_turn(prepared.analysis):
            return False
        if prepared.analysis.category in {"WELLBEING", "PLANNING"}:
            return False
        if prepared.analysis.category == "ACADEMIC" and (prepared.contexts or prepared.facts):
            return False
        return True

    def _direct_answer_rules(self, effective_query: str) -> str:
        normalized = self._normalize(effective_query)
        topics = self._query_topics(effective_query)
        rules = [
            "Luôn trả lời thẳng vào câu hỏi ở ngay câu đầu tiên, không vòng vo.",
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
        if "leadership" in topics:
            rules.extend(
                [
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
        if chat_mode == "extended":
            return (
                "Chế độ mở rộng: được phép dùng web_search khi cần kiểm tra thông tin mới hoặc khi RAG chưa đủ chắc. "
                "Trả lời đầy đủ hơn, nhưng vẫn ưu tiên nguồn UIT chính thức và không bịa nguồn."
            )
        return (
            "Chế độ nhanh: ưu tiên trả lời ngắn gọn bằng dữ liệu UIT đã có trong hệ thống và lịch sử chat. "
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

    def _focused_contexts(self, contexts: list[RetrievedContext], effective_query: str) -> list[RetrievedContext]:
        topics = self._query_topics(effective_query)
        if "leadership" not in topics:
            return contexts

        leadership_contexts = [
            item
            for item in contexts
            if item.document.is_official_uit
            and self._has_any(
                self._context_haystack(item),
                ["ban giam hieu", "pho hieu truong phu trach", "nguyen tan tran minh khang", "nguyen luu thuy ngan"],
            )
        ]
        return leadership_contexts[:3] if leadership_contexts else contexts[:1]

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
        analysis: QueryAnalysis | None = None,
        chat_mode: str = "quick",
    ) -> PreparedTurn:
        chat_mode = self._normalize_chat_mode(chat_mode)
        raw_effective_query = self._build_effective_query(db, session, content)
        effective_query = self.query_rewriter.rewrite(raw_effective_query)
        analysis = analysis or analyze_query(effective_query)
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
        grounding_brief = self._grounding_brief(contexts, effective_query)
        if grounding_brief:
            messages.append({"role": "system", "content": grounding_brief})
        facts_brief = self._facts_brief(facts)
        if facts_brief:
            messages.append({"role": "system", "content": facts_brief})
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

    async def answer(self, db: Session, session: ChatSession, content: str, chat_mode: str = "quick") -> ChatReply:
        chat_mode = self._normalize_chat_mode(chat_mode)
        effective_query = self.query_rewriter.rewrite(self._build_effective_query(db, session, content))
        analysis = analyze_query(effective_query)
        self._save_user_message(db, session, analysis, content)
        if self._is_crisis_turn(analysis):
            answer = self._crisis_answer()
            self._save_assistant_message(db, session, analysis, answer)
            return self._assistant_reply(session.id, analysis, [], self._crisis_action_suggestions(), answer)

        prepared = await self._prepare_turn(db, session, content, analysis, chat_mode)
        if self._should_low_confidence_refuse(prepared):
            answer = self._low_confidence_answer()
            self._save_assistant_message(db, session, prepared.analysis, answer)
            return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)
        try:
            answer = await self.llm.chat(
                prepared.messages,
                web_search_enabled=self._should_enable_web_search(prepared),
                web_search_max_results=2 if chat_mode == "quick" else None,
            )
        except Exception as exc:
            logger.error("[chat] llm chat thất bại: %s", exc)
            answer = self._fallback_answer(prepared.analysis.category, prepared.contexts)

        validation = self.citation_validator.clean_answer(answer, prepared.citations)
        self._save_assistant_message(db, session, prepared.analysis, validation.answer)
        return self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, validation.answer)

    async def stream_answer(self, db: Session, session: ChatSession, content: str, chat_mode: str = "quick") -> AsyncIterator[dict]:
        chat_mode = self._normalize_chat_mode(chat_mode)
        effective_query = self.query_rewriter.rewrite(self._build_effective_query(db, session, content))
        analysis = analyze_query(effective_query)
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
        yield {"type": "status", "label": "Studify đang ưu tiên an toàn..." if is_crisis else "Studify đang phân tích câu hỏi..."}
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

        if chat_mode == "extended":
            yield {"type": "status", "label": "Studify đang tìm dữ liệu UIT và có thể kiểm tra web sâu..."}
        else:
            yield {"type": "status", "label": "Studify đang tìm dữ liệu UIT, nếu thiếu sẽ tìm web nhanh..."}
        prepared = await self._prepare_turn(db, session, content, analysis, chat_mode)
        await asyncio.sleep(0)
        if self._should_low_confidence_refuse(prepared):
            answer = self._low_confidence_answer()
            for chunk in self._stream_text_chunks(answer):
                yield {"type": "chunk", "delta": chunk}
            self._save_assistant_message(db, session, prepared.analysis, answer)
            reply = self._assistant_reply(session.id, prepared.analysis, prepared.citations, prepared.suggestions, answer)
            yield {"type": "done", **reply.model_dump(mode="json")}
            return

        yield {"type": "status", "label": "Studify đang soạn câu trả lời..."}

        answer_parts: list[str] = []
        try:
            async for chunk in self.llm.stream_chat(
                prepared.messages,
                web_search_enabled=self._should_enable_web_search(prepared),
                web_search_max_results=2 if chat_mode == "quick" else None,
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
