from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.scripts.seed_advisor import seed_advisor_demo_data
from app.models.academic import AcademicEvent, ClassSchedule, ExamSchedule, Reminder, Task
from app.models.knowledge import (
    Announcement,
    CollectedDocument,
    ConfidenceLevel,
    ContentCategory,
    DataSource,
    Department,
    FAQ,
    SourceType,
    SupportResource,
)
from app.models.users import StudentProfile, User, UserRole
from app.models.wellbeing import MoodJournal, MoodState, SystemConfig


DEFAULT_SOURCES = [
    {
        "name": "Website chính UIT",
        "base_url": "https://www.uit.edu.vn",
        "domain": "uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 720,
    },
    {
        "name": "Cổng đào tạo DAA",
        "base_url": "https://daa.uit.edu.vn",
        "domain": "daa.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Cổng sinh viên",
        "base_url": "https://student.uit.edu.vn",
        "domain": "student.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 240,
    },
    {
        "name": "Phòng CTSV",
        "base_url": "https://ctsv.uit.edu.vn",
        "domain": "ctsv.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 240,
    },
    {
        "name": "Phòng Kế hoạch Tài chính",
        "base_url": "https://khtc.uit.edu.vn",
        "domain": "khtc.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 240,
    },
    {
        "name": "Courses UIT",
        "base_url": "https://courses.uit.edu.vn",
        "domain": "courses.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 720,
    },
    {
        "name": "Văn phòng Các chương trình đặc biệt",
        "base_url": "https://oep.uit.edu.vn/vi",
        "domain": "oep.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": True,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Công nghệ Phần mềm",
        "base_url": "https://se.uit.edu.vn",
        "domain": "se.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Công nghệ Thông tin",
        "base_url": "https://fit.uit.edu.vn",
        "domain": "fit.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Khoa học Máy tính",
        "base_url": "https://cs.uit.edu.vn",
        "domain": "cs.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Hệ thống Thông tin",
        "base_url": "https://httt.uit.edu.vn",
        "domain": "httt.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Mạng máy tính và Truyền thông",
        "base_url": "https://nc.uit.edu.vn",
        "domain": "nc.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Khoa Kỹ thuật Máy tính",
        "base_url": "https://fce.uit.edu.vn",
        "domain": "fce.uit.edu.vn",
        "source_type": SourceType.OFFICIAL,
        "is_official_uit": True,
        "is_enabled": False,
        "crawl_interval_minutes": 360,
    },
    {
        "name": "Admin Upload",
        "base_url": "https://studify.local/admin-upload",
        "domain": "studify.local",
        "source_type": SourceType.REFERENCE,
        "is_official_uit": False,
        "is_enabled": True,
        "crawl_interval_minutes": 10080,
    },
]


def upsert_default_sources(db: Session) -> dict[str, DataSource]:
    source_map = {item.domain: item for item in db.query(DataSource).all()}

    for payload in DEFAULT_SOURCES:
        source = source_map.get(payload["domain"])
        if source is None:
            source = DataSource(**payload)
            db.add(source)
            db.flush()
            source_map[source.domain] = source
            continue

        source.name = payload["name"]
        source.base_url = payload["base_url"]
        source.source_type = payload["source_type"]
        source.is_official_uit = payload["is_official_uit"]
        source.is_enabled = payload.get("is_enabled", True)
        source.crawl_interval_minutes = payload["crawl_interval_minutes"]

    return source_map


DEFAULT_SYSTEM_CONFIGS = [
    {
        "key": "chat_system_prompt",
        "value_json": {
            "prompt": "Bạn là Studify, trợ lý đồng hành cho sinh viên UIT. Trả lời tiếng Việt, rõ, ấm áp, không bịa nguồn, ưu tiên nguồn UIT chính thức."
        },
        "description": "System prompt cho chatbot chung.",
    },
    {
        "key": "wellbeing_keywords",
        "value_json": {"keywords": ["buồn", "stress", "áp lực", "mệt", "quá tải", "nản"]},
        "description": "Danh sách từ khóa cho mode wellbeing nhẹ.",
    },
    {
        "key": "knowledge_refresh_schedule",
        "value_json": {"enabled": True, "interval_hours": 72, "target_documents": 280, "retry_after_hours_on_failure": 6},
        "description": "Lịch làm mới corpus RAG định kỳ từ các nguồn UIT.",
    },
    {
        "key": "knowledge_refresh_runtime",
        "value_json": {
            "status": "IDLE",
            "last_started_at": None,
            "last_completed_at": None,
            "last_success_at": None,
            "last_trigger": None,
            "last_message": "Chưa có lượt làm mới corpus nào.",
            "next_run_at": None,
            "last_result": None,
        },
        "description": "Trạng thái lượt làm mới corpus gần nhất.",
    },
    {
        "key": "energy_support_threshold",
        "value_json": {"low_threshold": 2.4},
        "description": "Ngưỡng năng lượng thấp để bật gợi ý nhạc hoặc nhắc nhẹ.",
    },
]


def upsert_default_system_configs(db: Session) -> None:
    config_map = {item.key: item for item in db.query(SystemConfig).all()}
    for payload in DEFAULT_SYSTEM_CONFIGS:
        config = config_map.get(payload["key"])
        if config is None:
            db.add(SystemConfig(**payload))
            continue
        if payload["key"] in {"knowledge_refresh_schedule", "knowledge_refresh_runtime"}:
            config.value_json = {**payload["value_json"], **(config.value_json or {})}
        if config.description is None:
            config.description = payload["description"]


def upsert_student_account(
    db: Session,
    *,
    username: str,
    full_name: str,
    email: str,
    faculty: str,
    major: str,
    class_name: str,
    cohort: str,
    advisor_name: str,
) -> tuple[User, StudentProfile]:
    student = db.query(User).filter(User.username == username).first()
    if student is None:
        student = User(
            username=username,
            password_hash=hash_password(username),
            full_name=full_name,
            email=email,
            role=UserRole.STUDENT,
        )
        db.add(student)

    student.username = username
    student.password_hash = hash_password(username)
    student.full_name = full_name
    student.email = email
    student.role = UserRole.STUDENT
    student.is_active = True
    db.flush()

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == student.id).first()
    if profile is None:
        profile = db.query(StudentProfile).filter(StudentProfile.student_id == username).first()
    if profile is None:
        profile = StudentProfile(
            user_id=student.id,
            student_id=username,
            faculty=faculty,
            major=major,
            class_name=class_name,
            cohort=cohort,
            advisor_name=advisor_name,
        )
        db.add(profile)

    profile.user_id = student.id
    profile.student_id = username
    profile.faculty = faculty
    profile.major = major
    profile.class_name = class_name
    profile.cohort = cohort
    profile.advisor_name = advisor_name
    db.flush()
    return student, profile


def upsert_default_accounts(db: Session) -> tuple[User, User, StudentProfile]:
    admin = db.query(User).filter(User.username == "admin").first()
    if admin is None:
        admin = User(
            username="admin",
            password_hash=hash_password("admin"),
            full_name="Quản trị Studify",
            email="admin@studify.local",
            role=UserRole.ADMIN,
        )
        db.add(admin)

    admin.password_hash = hash_password("admin")
    admin.full_name = "Quản trị Studify"
    admin.email = "admin@studify.local"
    admin.role = UserRole.ADMIN
    admin.is_active = True

    legacy_student = db.query(User).filter(User.username == "22520001").first()
    current_student = db.query(User).filter(User.username == "24522045").first()
    if legacy_student is not None and current_student is None:
        legacy_student.username = "24522045"

    student, profile = upsert_student_account(
        db,
        username="24522045",
        full_name="Võ Quang Vũ",
        email="24522045@gm.uit.edu.vn",
        faculty="Khoa Khoa học Máy tính",
        major="Khoa học Máy tính",
        class_name="KHMT2022",
        cohort="2022-2026",
        advisor_name="TS. Trần Văn Hưng",
    )
    upsert_student_account(
        db,
        username="24520033",
        full_name="Đặng Minh Tú",
        email="24520033@gm.uit.edu.vn",
        faculty="Khoa Mạng máy tính và Truyền thông",
        major="Mạng máy tính và Truyền thông dữ liệu",
        class_name="MMT2022",
        cohort="2022-2026",
        advisor_name="ThS. Phạm Minh Tuấn",
    )
    (
        db.query(Task)
        .filter(Task.status.in_(["TODO", "IN_PROGRESS"]))
        .update({"status": "OPEN"}, synchronize_session=False)
    )
    return admin, student, profile


def seed(db: Session) -> None:
    source_map = upsert_default_sources(db)
    upsert_default_system_configs(db)
    _, student, profile = upsert_default_accounts(db)
    profile_map = {item.student_id: item for item in db.query(StudentProfile).all()}
    seed_advisor_demo_data(db, profile_map)
    if db.query(Announcement.id).first() is not None:
        db.commit()
        return

    departments = [
        Department(name="Phòng Đào tạo Đại học", description="Đầu mối học vụ và kế hoạch đào tạo."),
        Department(name="Phòng Công tác Sinh viên", description="Đầu mối hỗ trợ sinh viên, học bổng, tâm lý."),
    ]
    db.add_all(departments)

    categories = [
        ContentCategory(code="ACADEMIC", display_name="Học vụ"),
        ContentCategory(code="ANNOUNCEMENT", display_name="Thông báo"),
        ContentCategory(code="SCHEDULE", display_name="Lịch học vụ"),
        ContentCategory(code="EXAM", display_name="Lịch thi"),
        ContentCategory(code="TUITION", display_name="Học phí"),
        ContentCategory(code="SCHOLARSHIP", display_name="Học bổng"),
        ContentCategory(code="PROCEDURE", display_name="Thủ tục"),
        ContentCategory(code="WELLBEING", display_name="Tâm lý"),
        ContentCategory(code="SKILL", display_name="Kỹ năng"),
    ]
    db.add_all(categories)
    db.flush()

    now = datetime.now(timezone.utc)
    documents = [
        CollectedDocument(
            title="Kế hoạch xét tốt nghiệp học kỳ 2 năm học 2025-2026",
            url="https://student.uit.edu.vn/thong-bao/ke-hoach-xet-tot-nghiep-hk2-2025-2026",
            data_source_id=source_map["student.uit.edu.vn"].id,
            category_id=categories[1].id,
            group_name="Tốt nghiệp",
            published_at=now - timedelta(days=2),
            updated_source_at=now - timedelta(days=1),
            tags=["tốt nghiệp", "học vụ", "khóa 2022"],
            raw_content="Sinh viên kiểm tra điều kiện tốt nghiệp, chuẩn đầu ra ngoại ngữ, chứng chỉ và công nợ học phí.",
            cleaned_content="Sinh viên UIT cần kiểm tra điều kiện tốt nghiệp, chuẩn đầu ra ngoại ngữ, công nợ học phí và hồ sơ minh chứng trước ngày 25/04/2026.",
            summary="Sinh viên UIT cần hoàn tất hồ sơ xét tốt nghiệp trước ngày 25/04/2026.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
            vector_metadata={"source": "student.uit.edu.vn"},
        ),
        CollectedDocument(
            title="Hướng dẫn xin giấy xác nhận sinh viên trực tuyến",
            url="https://daa.uit.edu.vn/huong-dan/giay-xac-nhan-sinh-vien-truc-tuyen",
            data_source_id=source_map["daa.uit.edu.vn"].id,
            category_id=categories[0].id,
            group_name="Thủ tục",
            published_at=now - timedelta(days=10),
            updated_source_at=now - timedelta(days=8),
            tags=["giấy xác nhận", "thủ tục", "daa"],
            raw_content="Sinh viên truy cập cổng đào tạo, chọn mục biểu mẫu và điền yêu cầu xác nhận.",
            cleaned_content="Sinh viên truy cập cổng đào tạo DAA, đăng nhập bằng tài khoản sinh viên, chọn biểu mẫu giấy xác nhận, kiểm tra thông tin và gửi yêu cầu. Kết quả được phản hồi qua email trường.",
            summary="Quy trình xin giấy xác nhận sinh viên qua cổng DAA.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
            vector_metadata={"source": "daa.uit.edu.vn"},
        ),
        CollectedDocument(
            title="Thông tin tham vấn tâm lý và Không gian Chia sẻ UIT",
            url="https://ctsv.uit.edu.vn/tam-ly/khong-gian-chia-se-a104",
            data_source_id=source_map["ctsv.uit.edu.vn"].id,
            category_id=categories[2].id,
            group_name="Tâm lý",
            published_at=now - timedelta(days=6),
            updated_source_at=now - timedelta(days=3),
            tags=["tâm lý", "ctsv", "không gian chia sẻ"],
            raw_content="Phòng CTSV tổ chức không gian chia sẻ tại phòng A104 và hỗ trợ kết nối chuyên gia.",
            cleaned_content="Phòng CTSV tổ chức Không gian Chia sẻ tại phòng A104 nhằm hỗ trợ sinh viên cần lắng nghe, tư vấn ban đầu và kết nối chuyên gia tâm lý khi cần.",
            summary="Nguồn hỗ trợ tâm lý ban đầu dành cho sinh viên UIT tại phòng A104.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_wellbeing_related=True,
            vector_metadata={"source": "ctsv.uit.edu.vn"},
        ),
        CollectedDocument(
            title="Tổng quan chương trình Chất lượng cao tại UIT",
            url="https://oep.uit.edu.vn/vi/tong-quan-ve-chuong-trinh-chat-luong-cao",
            data_source_id=source_map["oep.uit.edu.vn"].id,
            category_id=categories[0].id,
            group_name="Chương trình đặc biệt",
            published_at=now - timedelta(days=12),
            updated_source_at=now - timedelta(days=5),
            tags=["oep", "chất lượng cao", "chương trình đặc biệt"],
            raw_content="OEP phụ trách chương trình chất lượng cao, cung cấp thông tin học tập, học phí và tư vấn dành cho sinh viên theo học chương trình đặc biệt.",
            cleaned_content="Văn phòng Các chương trình đặc biệt OEP cung cấp thông tin tổng quan về chương trình chất lượng cao, lịch học tập, hỗ trợ học vụ và đầu mối liên hệ cho sinh viên đang theo học các chương trình đặc biệt tại UIT.",
            summary="Thông tin tổng quan dành cho sinh viên các chương trình đặc biệt tại UIT.",
            confidence_level=ConfidenceLevel.HIGH,
            is_official_uit=True,
            is_academic_related=True,
            vector_metadata={"source": "oep.uit.edu.vn"},
        ),
        CollectedDocument(
            title="Mẹo lập kế hoạch tuần cho sinh viên công nghệ",
            url="https://studify.example/reference/weekly-planning",
            data_source_id=None,
            category_id=categories[3].id,
            group_name="Kỹ năng",
            published_at=now - timedelta(days=14),
            updated_source_at=now - timedelta(days=14),
            tags=["tham khảo", "kỹ năng", "lập kế hoạch"],
            raw_content="Gợi ý chia việc theo 3 nhóm ưu tiên và dành block nghỉ ngắn sau mỗi 90 phút.",
            cleaned_content="Nguồn tham khảo: chia việc theo ba mức ưu tiên, gom deadline theo tuần, giữ block nghỉ ngắn 10-15 phút sau mỗi 90 phút học.",
            summary="Nguồn tham khảo ngoài UIT về lập kế hoạch tuần.",
            confidence_level=ConfidenceLevel.MEDIUM,
            is_official_uit=False,
            is_wellbeing_related=True,
            vector_metadata={"source": "reference"},
        ),
    ]
    db.add_all(documents)
    db.flush()

    announcements = [
        Announcement(
            title="Thông báo mở đăng ký học phần học kỳ hè 2025-2026",
            short_description="Sinh viên theo dõi thời gian đăng ký học phần và chuẩn bị học phí.",
            url="https://student.uit.edu.vn/thong-bao/dang-ky-hoc-phan-he-2025-2026",
            group_name="Học vụ",
            is_featured=True,
            published_at=now - timedelta(days=1),
            document_id=documents[0].id,
            is_official_uit=True,
            tags=["đăng ký học phần", "học vụ"],
        ),
        Announcement(
            title="CTSV phát động tuần lễ kỹ năng và hỗ trợ tâm lý đầu học kỳ",
            short_description="Chuỗi workshop kỹ năng học tập, quản lý áp lực và tư vấn ban đầu.",
            url="https://ctsv.uit.edu.vn/tin-tuc/tuan-le-ky-nang-va-ho-tro-tam-ly",
            group_name="Tâm lý",
            is_featured=True,
            published_at=now - timedelta(days=3),
            document_id=documents[2].id,
            is_official_uit=True,
            tags=["ctsv", "tâm lý", "kỹ năng"],
        ),
        Announcement(
            title="OEP cập nhật thông tin chương trình Chất lượng cao cho sinh viên",
            short_description="Sinh viên các chương trình đặc biệt có thể theo dõi thông tin học tập, học phí và đầu mối hỗ trợ tại OEP.",
            url="https://oep.uit.edu.vn/vi/tong-quan-ve-chuong-trinh-chat-luong-cao",
            group_name="Chương trình đặc biệt",
            is_featured=False,
            published_at=now - timedelta(days=5),
            document_id=documents[3].id,
            is_official_uit=True,
            tags=["oep", "chương trình đặc biệt"],
        ),
    ]
    db.add_all(announcements)

    db.add_all(
        [
            AcademicEvent(
                title="Mở cổng đăng ký học phần học kỳ hè",
                group_name="Đăng ký học phần",
                description="Sinh viên kiểm tra lịch cá nhân và tránh trùng lịch học.",
                starts_at=now + timedelta(days=2),
                ends_at=now + timedelta(days=4),
                detail_url=announcements[0].url,
                is_featured=True,
            ),
            AcademicEvent(
                title="Đóng học phí đợt 1",
                group_name="Học phí",
                description="Hoàn tất trước khi hệ thống khóa đăng ký học phần.",
                starts_at=now + timedelta(days=7),
                ends_at=now + timedelta(days=10),
                is_featured=True,
            ),
        ]
    )

    moods = [
        MoodState(code="VERY_GOOD", display_name="Rất ổn", color="#8EF6B4", intensity=5),
        MoodState(code="GOOD", display_name="Ổn", color="#9AD6FF", intensity=4),
        MoodState(code="TIRED", display_name="Hơi mệt", color="#FFD98E", intensity=3),
        MoodState(code="PRESSURED", display_name="Áp lực", color="#FFAC78", intensity=2),
        MoodState(code="OVERLOADED", display_name="Quá tải", color="#FF7B7B", intensity=1),
    ]
    db.add_all(moods)
    db.flush()

    db.add(
        MoodJournal(
            user_id=student.id,
            mood_state_id=moods[2].id,
            short_note="Tuần này bài tập nhiều, cần sắp xếp lại deadline.",
            energy_level=3,
            needs_human_support=False,
        )
    )

    db.add_all(
        [
            SupportResource(
                title="Không gian Chia sẻ UIT - phòng A104",
                description="Điểm chạm hỗ trợ tâm lý ban đầu, lắng nghe và kết nối chuyên gia khi cần.",
                resource_type="Hỗ trợ tâm lý",
                owner_unit="Phòng Công tác Sinh viên",
                link_url="https://ctsv.uit.edu.vn",
                contact="ctsv@uit.edu.vn",
                is_official_uit=True,
                urgent_priority=10,
            ),
            SupportResource(
                title="Tư vấn học vụ DAA",
                description="Kênh hỗ trợ về CTĐT, giấy tờ, xét tốt nghiệp và học phần.",
                resource_type="Học vụ",
                owner_unit="Phòng Đào tạo Đại học",
                link_url="https://daa.uit.edu.vn",
                contact="daa@uit.edu.vn",
                is_official_uit=True,
                urgent_priority=6,
            ),
        ]
    )

    db.add_all(
        [
            FAQ(group_name="Học vụ", question="Cách xin giấy xác nhận sinh viên?", answer="Vào DAA, chọn biểu mẫu và gửi yêu cầu trực tuyến.", priority=10),
            FAQ(group_name="Tâm lý", question="Khi áp lực nhiều mình nên làm gì?", answer="Bắt đầu bằng nghỉ ngắn, chia việc nhỏ và cân nhắc liên hệ CTSV nếu cần người hỗ trợ.", priority=9),
        ]
    )

    db.add_all(
        [
            ClassSchedule(
                student_profile_id=profile.id,
                course_code="CS221",
                course_name="Trí tuệ nhân tạo",
                lecturer_name="TS. Lê Hoàng Phúc",
                room_name="A306",
                weekday=2,
                period_start=1,
                period_end=3,
                starts_at=now + timedelta(days=1, hours=1),
                ends_at=now + timedelta(days=1, hours=4),
                display_color="#4F7DF5",
            ),
            ClassSchedule(
                student_profile_id=profile.id,
                course_code="SE104",
                course_name="Nhập môn Công nghệ phần mềm",
                lecturer_name="ThS. Nguyễn Thu Hà",
                room_name="E201",
                weekday=4,
                period_start=4,
                period_end=6,
                starts_at=now + timedelta(days=2, hours=6),
                ends_at=now + timedelta(days=2, hours=9),
                display_color="#2FBF8C",
            ),
            ExamSchedule(
                student_profile_id=profile.id,
                course_code="CS221",
                course_name="Trí tuệ nhân tạo",
                room_name="C309",
                exam_type="Tự luận",
                starts_at=now + timedelta(days=14, hours=2),
                ends_at=now + timedelta(days=14, hours=4),
            ),
        ]
    )

    task = Task(
        user_id=student.id,
        title="Hoàn tất báo cáo đồ án tuần 6",
        description="Cập nhật phần thử nghiệm và kết luận.",
        task_type="Đồ án",
        priority="HIGH",
        due_at=now + timedelta(days=3),
        is_recurring=False,
    )
    db.add(task)
    db.flush()
    db.add(
        Reminder(
            task_id=task.id,
            remind_at=now + timedelta(days=2, hours=8),
            channel="IN_APP",
            message="Nhớ chốt báo cáo đồ án tuần 6 trước tối mai.",
        )
    )

    db.commit()


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
