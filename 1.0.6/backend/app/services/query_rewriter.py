from __future__ import annotations

import re
import unicodedata

ABBREVIATION_MAP = {
    "dkhp": "đăng ký học phần",
    "tkb": "thời khóa biểu",
    "ctdt": "chương trình đào tạo",
    "clc": "chất lượng cao",
    "cntt": "công nghệ thông tin",
    "khmt": "khoa học máy tính",
    "ktmt": "kỹ thuật máy tính",
    "mmt": "mạng máy tính",
    "httt": "hệ thống thông tin",
    "kkht": "khuyến khích học tập",
    "ta": "tiếng Anh",
}

TOPIC_EXPANSIONS = {
    "english": "chuẩn đầu ra tiếng Anh UIT TOEIC IELTS VSTEP VNU-EPT điều kiện tốt nghiệp sinh viên",
    "registration": "đăng ký học phần UIT xác nhận ĐKHP thời khóa biểu học kỳ sinh viên",
    "tuition": "học phí UIT thời hạn đóng học phí phương thức thanh toán phòng kế hoạch tài chính",
    "scholarship": "học bổng UIT khuyến khích học tập CTSV điều kiện xét học bổng hạn đăng ký",
    "graduation": "xét tốt nghiệp UIT điều kiện tốt nghiệp hồ sơ đợt xét tốt nghiệp",
    "procedure": "thủ tục sinh viên UIT giấy xác nhận sinh viên bảo lưu tạm ngưng liên hệ phòng ban",
    "schedule": "lịch học lịch thi thời khóa biểu UIT học kỳ cập nhật mới nhất",
    "annual_plan": "kế hoạch đào tạo năm học UIT lịch nghỉ học kỳ hè khai giảng Tết",
    "academic_warning": "cảnh báo học vụ UIT điều kiện cảnh báo xử lý học vụ sinh viên",
    "curriculum": "chương trình đào tạo UIT CTĐT ngành học khóa học môn học tiên quyết",
    "special_program": "chương trình đặc biệt UIT OEP tài năng chất lượng cao tiên tiến BCU UON",
}


class QueryRewriter:
    def normalize_ascii(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
        stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        compact = re.sub(r"[^a-z0-9]+", " ", stripped)
        return re.sub(r"\s+", " ", compact).strip()

    def expand_abbreviations(self, query: str) -> str:
        rewritten = query or ""
        normalized = self.normalize_ascii(rewritten)
        additions: list[str] = []
        for abbreviation, expansion in ABBREVIATION_MAP.items():
            if re.search(rf"\b{re.escape(abbreviation)}\b", normalized):
                additions.append(expansion)
        if not additions:
            return rewritten.strip()
        return " ".join([rewritten.strip(), *additions]).strip()

    def topics(self, query: str) -> set[str]:
        normalized = self.normalize_ascii(query)
        topic_keywords = {
            "english": ["tieng anh", "ngoai ngu", "toeic", "ielts", "toefl", "vstep", "vnu ept", "chuan dau ra", "chuan ta"],
            "registration": ["dang ky hoc phan", "dkhp", "hoc phan", "xac nhan dkhp"],
            "tuition": ["hoc phi", "dong hoc phi", "thu hoc phi", "khtc"],
            "scholarship": ["hoc bong", "kkht", "khuyen khich hoc tap"],
            "graduation": ["tot nghiep", "xet tot nghiep", "ra truong"],
            "procedure": ["thu tuc", "giay xac nhan", "bao luu", "tam ngung", "thoi hoc", "chuyen nganh"],
            "schedule": ["lich hoc", "lich thi", "tkb", "thoi khoa bieu"],
            "annual_plan": ["ke hoach nam", "ke hoach dao tao", "nghi he", "hoc ky he", "tet"],
            "academic_warning": ["canh bao hoc vu", "canh bao hoc tap", "xu ly hoc vu"],
            "curriculum": ["ctdt", "chuong trinh dao tao", "khung chuong trinh", "nganh hoc"],
            "special_program": ["oep", "tai nang", "chat luong cao", "cttn", "ctclc", "cttt", "bcu", "uon"],
            "wellbeing": ["stress", "ap luc", "met", "buon", "qua tai", "lo au"],
            "planning": ["len ke hoach", "sap xep", "deadline", "nhac viec"],
            "announcement": ["thong bao", "moi nhat", "cap nhat", "tin moi"],
        }
        matched: set[str] = set()
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                # So khớp theo ranh giới từ, tránh khớp chuỗi con (ví dụ "uon"
                # khớp nhầm bên trong "muốn" -> gắn sai chủ đề special_program).
                if re.search(rf"\b{re.escape(keyword)}\b", normalized):
                    matched.add(topic)
                    break
        return matched or {"general"}

    def rewrite(self, query: str) -> str:
        expanded = self.expand_abbreviations(query)
        topics = self.topics(expanded)
        additions = [TOPIC_EXPANSIONS[topic] for topic in topics if topic in TOPIC_EXPANSIONS]
        if not additions:
            return expanded
        # Giữ NGUYÊN câu gốc; chỉ nối thêm các token mở rộng chưa xuất hiện.
        # Trước đây việc dedup trên toàn bộ chuỗi gộp đã nuốt mất token của
        # người dùng khi hai từ khác nghĩa trùng dạng bỏ dấu (ví dụ "tự" và
        # "tử" cùng key "tu") -> phá hỏng cả ý nghĩa câu hỏi lẫn dò khủng hoảng.
        seen = {key for token in expanded.split() if (key := self.normalize_ascii(token))}
        extra_tokens: list[str] = []
        for token in " ".join(additions).split():
            key = self.normalize_ascii(token)
            if not key or key in seen:
                continue
            seen.add(key)
            extra_tokens.append(token)
        if not extra_tokens:
            return expanded
        return " ".join([expanded, *extra_tokens])

# Module-level alias used by tests
normalize_ascii = QueryRewriter().normalize_ascii
