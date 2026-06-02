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
        faculty="Khoa Mạng máy tính và Truyền thông",
        major="An toàn thông tin",
        class_name="ATTN2024",
        cohort="2022-2026",
        advisor_name="TS. Trần Văn Hưng",
    )
    upsert_student_account(
        db,
        username="24520033",
        full_name="Đặng Minh Tú",
        email="24520033@gm.uit.edu.vn",
        faculty="Khoa Khoa học Máy tính",
        major="Khoa học Máy tính",
        class_name="KHTN2024",
        cohort="2022-2026",
        advisor_name="ThS. Phạm Minh Tuấn",
    )
    (
        db.query(Task)
        .filter(Task.status.in_(["TODO", "IN_PROGRESS"]))
        .update({"status": "OPEN"}, synchronize_session=False)
    )
    return admin, student, profile


VN_TIMEZONE = timezone(timedelta(hours=7))

PERIOD_START_TIMES: dict[int, tuple[int, int]] = {
    1: (7, 30),
    2: (8, 15),
    3: (9, 0),
    4: (10, 0),
    5: (10, 45),
    6: (13, 0),
    7: (13, 45),
    8: (14, 30),
    9: (15, 30),
    10: (16, 15),
}


def vietnam_weekday_to_iso(weekday: int) -> int:
    if weekday in {1, 8}:
        return 7
    return max(1, min(6, weekday - 1))


def next_occurrence(
    now: datetime,
    *,
    weekday: int,
    hour: int,
    minute: int = 0,
    duration_hours: int = 3,
    week_offset: int = 0,
) -> tuple[datetime, datetime]:
    anchor = now.astimezone(VN_TIMEZONE).replace(second=0, microsecond=0)
    days_ahead = (vietnam_weekday_to_iso(weekday) - anchor.isoweekday()) % 7
    start = (anchor + timedelta(days=days_ahead + week_offset * 7)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if week_offset == 0 and start <= now:
        start += timedelta(days=7)
    end = start + timedelta(hours=duration_hours)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def next_period_block(now: datetime, *, weekday: int, period_start: int, period_end: int) -> tuple[datetime, datetime]:
    hour, minute = PERIOD_START_TIMES[period_start]
    start, _ = next_occurrence(now, weekday=weekday, hour=hour, minute=minute, duration_hours=1)
    end = start + timedelta(minutes=(period_end - period_start + 1) * 45)
    return start, end


def vietnam_datetime(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=VN_TIMEZONE).astimezone(timezone.utc)


def student_class_item(
    now: datetime,
    *,
    course_code: str,
    course_name: str,
    lecturer_name: str,
    room_name: str,
    weekday: int,
    period_start: int,
    period_end: int,
    display_color: str,
) -> dict[str, object]:
    starts_at, ends_at = next_period_block(now, weekday=weekday, period_start=period_start, period_end=period_end)
    return {
        "course_code": course_code,
        "course_name": course_name,
        "lecturer_name": lecturer_name,
        "room_name": room_name,
        "weekday": weekday,
        "period_start": period_start,
        "period_end": period_end,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "display_color": display_color,
    }


def replace_student_schedule(
    db: Session,
    *,
    profile: StudentProfile,
    class_items: list[dict[str, object]],
    exam_items: list[dict[str, object]],
) -> None:
    db.query(ClassSchedule).filter(ClassSchedule.student_profile_id == profile.id).delete(synchronize_session=False)
    db.query(ExamSchedule).filter(ExamSchedule.student_profile_id == profile.id).delete(synchronize_session=False)
    db.flush()

    db.add_all([ClassSchedule(student_profile_id=profile.id, **item) for item in class_items])
    db.add_all([ExamSchedule(student_profile_id=profile.id, **item) for item in exam_items])


def seed_student_schedules(db: Session, profile_map: dict[str, StudentProfile], now: datetime) -> None:
    vu_profile = profile_map.get("24522045")
    tu_profile = profile_map.get("24520033")

    if vu_profile is not None:
        vu_exam_nt106_start = vietnam_datetime(2026, 6, 2, 7, 30)
        vu_exam_nt208_start = vietnam_datetime(2026, 6, 4, 13, 30)

        replace_student_schedule(
            db,
            profile=vu_profile,
            class_items=[
                student_class_item(
                    now,
                    course_code="NT132.Q21.ANTN.1",
                    course_name="Quản trị mạng và hệ thống - VN",
                    lecturer_name="Đỗ Hoàng Hiền",
                    room_name="B5.04 (PM) - Cách 2 tuần",
                    weekday=5,
                    period_start=1,
                    period_end=3,
                    display_color="#16A34A",
                ),
                student_class_item(
                    now,
                    course_code="NT208.Q21.ANTN.1",
                    course_name="Lập trình ứng dụng web - VN",
                    lecturer_name="Trần Tuấn Dũng",
                    room_name="B5.04 (PM) - Cách 2 tuần",
                    weekday=5,
                    period_start=1,
                    period_end=3,
                    display_color="#16A34A",
                ),
                student_class_item(
                    now,
                    course_code="NT132.Q21.ANTN",
                    course_name="Quản trị mạng và hệ thống - VN",
                    lecturer_name="Nguyễn Duy",
                    room_name="C307",
                    weekday=7,
                    period_start=1,
                    period_end=3,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="NT140.Q21.ANTN",
                    course_name="An toàn mạng - VN",
                    lecturer_name="Phạm Văn Hậu, Nghi Hoàng Khoa",
                    room_name="C308",
                    weekday=4,
                    period_start=3,
                    period_end=5,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="NT106.Q21.ANTN",
                    course_name="Lập trình mạng căn bản - VN",
                    lecturer_name="Đỗ Thị Hương Lan",
                    room_name="C308",
                    weekday=2,
                    period_start=4,
                    period_end=5,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="NT106.Q21.ANTN",
                    course_name="Lập trình mạng căn bản - VN",
                    lecturer_name="Đỗ Thị Hương Lan",
                    room_name="C308",
                    weekday=4,
                    period_start=4,
                    period_end=5,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="SS008.Q28",
                    course_name="Kinh tế chính trị Mác - Lênin - VN",
                    lecturer_name="Hà Thị Việt Thùy",
                    room_name="B1.14",
                    weekday=7,
                    period_start=4,
                    period_end=5,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="NT106.Q21.ANTN.1",
                    course_name="Lập trình mạng căn bản - VN",
                    lecturer_name="Đỗ Thị Hương Lan",
                    room_name="B5.04 (PM) - Cách 2 tuần",
                    weekday=2,
                    period_start=6,
                    period_end=8,
                    display_color="#16A34A",
                ),
                student_class_item(
                    now,
                    course_code="NT140.Q21.ANTN.1",
                    course_name="An toàn mạng - VN",
                    lecturer_name="Trương Thị Hoàng Hảo",
                    room_name="B4.06 (PM) - Cách 2 tuần",
                    weekday=4,
                    period_start=6,
                    period_end=8,
                    display_color="#16A34A",
                ),
                student_class_item(
                    now,
                    course_code="NT208.Q21.ANTN",
                    course_name="Lập trình ứng dụng web - VN",
                    lecturer_name="Trần Tuấn Dũng",
                    room_name="C306",
                    weekday=5,
                    period_start=6,
                    period_end=8,
                    display_color="#2563EB",
                ),
                student_class_item(
                    now,
                    course_code="PE231.Q29",
                    course_name="Giáo dục thể chất 1 - VN",
                    lecturer_name="Huỳnh Quốc Khánh",
                    room_name="Sân bóng bàn",
                    weekday=7,
                    period_start=6,
                    period_end=8,
                    display_color="#2563EB",
                ),
            ],
            exam_items=[
                {
                    "course_code": "NT106",
                    "course_name": "Lập trình mạng căn bản",
                    "room_name": "B1.20",
                    "exam_type": "CK • Tiết 12 • VD/VD",
                    "starts_at": vu_exam_nt106_start,
                    "ends_at": vu_exam_nt106_start + timedelta(minutes=90),
                },
                {
                    "course_code": "NT208",
                    "course_name": "Lập trình ứng dụng web",
                    "room_name": "E41",
                    "exam_type": "CK • Tiết 67890 • VD/VD",
                    "starts_at": vu_exam_nt208_start,
                    "ends_at": vu_exam_nt208_start + timedelta(hours=3, minutes=30),
                },
            ],
        )

    if tu_profile is not None:
        tu_cs331_start, tu_cs331_end = next_occurrence(now, weekday=3, hour=7, minute=30)
        tu_cs338_start, tu_cs338_end = next_occurrence(now, weekday=5, hour=13, minute=0)
        tu_cs399_start, tu_cs399_end = next_occurrence(now, weekday=6, hour=10, minute=0)
        tu_exam_cs331_start, tu_exam_cs331_end = next_occurrence(now, weekday=4, hour=7, minute=30, duration_hours=2, week_offset=2)
        tu_exam_cs338_start, tu_exam_cs338_end = next_occurrence(now, weekday=6, hour=13, minute=30, duration_hours=2, week_offset=3)

        replace_student_schedule(
            db,
            profile=tu_profile,
            class_items=[
                {
                    "course_code": "CS331",
                    "course_name": "Thiết kế và phân tích thuật toán",
                    "lecturer_name": "TS. Lê Hoàng Phúc",
                    "room_name": "A306",
                    "weekday": 3,
                    "period_start": 1,
                    "period_end": 3,
                    "starts_at": tu_cs331_start,
                    "ends_at": tu_cs331_end,
                    "display_color": "#4F7DF5",
                },
                {
                    "course_code": "CS338",
                    "course_name": "Cơ sở dữ liệu",
                    "lecturer_name": "ThS. Nguyễn Thu Hà",
                    "room_name": "E201",
                    "weekday": 5,
                    "period_start": 7,
                    "period_end": 9,
                    "starts_at": tu_cs338_start,
                    "ends_at": tu_cs338_end,
                    "display_color": "#2FBF8C",
                },
                {
                    "course_code": "CS399",
                    "course_name": "Phương pháp nghiên cứu khoa học",
                    "lecturer_name": "TS. Phan Minh Quân",
                    "room_name": "A114",
                    "weekday": 6,
                    "period_start": 4,
                    "period_end": 6,
                    "starts_at": tu_cs399_start,
                    "ends_at": tu_cs399_end,
                    "display_color": "#7C3AED",
                },
            ],
            exam_items=[
                {
                    "course_code": "CS331",
                    "course_name": "Thiết kế và phân tích thuật toán",
                    "room_name": "A204",
                    "exam_type": "Tự luận",
                    "starts_at": tu_exam_cs331_start,
                    "ends_at": tu_exam_cs331_end,
                },
                {
                    "course_code": "CS338",
                    "course_name": "Cơ sở dữ liệu",
                    "room_name": "E207",
                    "exam_type": "Tự luận + thực hành",
                    "starts_at": tu_exam_cs338_start,
                    "ends_at": tu_exam_cs338_end,
                },
            ],
        )


def upsert_uit_knowledge_docs(db: Session, source_map: dict[str, DataSource]) -> None:
    """Upsert additional UIT knowledge documents by URL so they apply to existing DBs too."""
    now = datetime.now(timezone.utc)
    category_map = {item.code: item for item in db.query(ContentCategory).all()}
    announcement_cat = category_map.get("ANNOUNCEMENT")
    academic_cat = category_map.get("ACADEMIC")
    skill_cat = category_map.get("SKILL")
    wellbeing_cat = category_map.get("WELLBEING")

    extra_docs = [
        {
            "title": "Ban Giám hiệu Trường Đại học Công nghệ Thông tin UIT",
            "url": "https://www.uit.edu.vn/bai-viet/ban-giam-hieu",
            "data_source_id": source_map.get("uit.edu.vn") and source_map["uit.edu.vn"].id,
            "category_id": announcement_cat.id if announcement_cat else None,
            "group_name": "Giới thiệu trường",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["ban giám hiệu", "hiệu trưởng", "phó hiệu trưởng phụ trách", "lãnh đạo", "UIT"],
            "raw_content": (
                "Trang Ban Giám hiệu chính thức của Trường Đại học Công nghệ Thông tin - ĐHQG-HCM hiện liệt kê "
                "PGS.TS. Nguyễn Tấn Trần Minh Khang với chức danh Phó hiệu trưởng phụ trách và "
                "PGS.TS. Nguyễn Lưu Thùy Ngân với chức danh Phó hiệu trưởng. "
                "Trang hiện không ghi một người giữ chức danh Hiệu trưởng."
            ),
            "cleaned_content": (
                "Ban Giám hiệu Trường Đại học Công nghệ Thông tin - ĐHQG-HCM theo trang chính thức của UIT:\n"
                "- PGS.TS. Nguyễn Tấn Trần Minh Khang: Phó hiệu trưởng phụ trách. Email: khangnttm[at]uit.edu.vn.\n"
                "  Phụ trách công tác tổ chức - cán bộ, kế hoạch - tài chính, xây dựng cơ bản, cơ sở vật chất, "
                "công tác sinh viên, Đoàn - Hội, hướng nghiệp, tư vấn tuyển sinh và quan hệ đối ngoại liên quan đến mảng phụ trách.\n"
                "- PGS.TS. Nguyễn Lưu Thùy Ngân: Phó hiệu trưởng. Email: ngannlt[at]uit.edu.vn.\n"
                "  Phụ trách đào tạo sau đại học, khoa học công nghệ, khởi nghiệp, pháp chế và đảm bảo chất lượng, "
                "quan hệ đối ngoại, đào tạo đại học, tuyển sinh, các chương trình đào tạo đặc biệt, thư viện và giáo trình.\n"
                "Lưu ý quan trọng: trang chính thức hiện không liệt kê chức danh Hiệu trưởng; khi sinh viên hỏi 'Hiệu trưởng là ai?', "
                "hãy trả lời rằng nguồn UIT hiện tại chỉ ghi PGS.TS. Nguyễn Tấn Trần Minh Khang là Phó hiệu trưởng phụ trách, "
                "không nên khẳng định có Hiệu trưởng nếu nguồn không ghi.\n"
                "Nguồn: https://www.uit.edu.vn/bai-viet/ban-giam-hieu"
            ),
            "summary": "Trang Ban Giám hiệu UIT hiện ghi PGS.TS. Nguyễn Tấn Trần Minh Khang là Phó hiệu trưởng phụ trách và PGS.TS. Nguyễn Lưu Thùy Ngân là Phó hiệu trưởng; trang không ghi chức danh Hiệu trưởng.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "uit.edu.vn", "category": "ban-giam-hieu", "verified_at": "2026-05-13"},
        },
        {
            "title": "Giới thiệu chung Trường Đại học Công nghệ Thông tin - UIT",
            "url": "https://www.uit.edu.vn/gioi-thieu",
            "data_source_id": source_map.get("uit.edu.vn") and source_map["uit.edu.vn"].id,
            "category_id": announcement_cat.id if announcement_cat else None,
            "group_name": "Giới thiệu trường",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["giới thiệu", "UIT", "lịch sử", "sứ mệnh"],
            "raw_content": (
                "Trường Đại học Công nghệ Thông tin (UIT) là thành viên của Đại học Quốc gia TP.HCM, "
                "được thành lập năm 2006. Trụ sở đặt tại Khu phố 6, Phường Linh Trung, TP. Thủ Đức, TP.HCM. "
                "UIT đào tạo các ngành liên quan đến công nghệ thông tin, truyền thông, an toàn thông tin và khoa học máy tính."
            ),
            "cleaned_content": (
                "Trường Đại học Công nghệ Thông tin (UIT) - Đại học Quốc gia TP.HCM:\n"
                "- Thành lập: năm 2006\n"
                "- Địa chỉ: Khu phố 6, Phường Linh Trung, Thành phố Thủ Đức, TP.HCM\n"
                "- Điện thoại: (028) 37251993\n"
                "- Email: info@uit.edu.vn\n"
                "- Website: https://www.uit.edu.vn\n"
                "Sứ mệnh: Đào tạo nguồn nhân lực chất lượng cao trong lĩnh vực CNTT, nghiên cứu và chuyển giao công nghệ, "
                "phục vụ sự phát triển kinh tế - xã hội.\n"
                "Các ngành đào tạo: Công nghệ Thông tin, Khoa học Máy tính, Hệ thống Thông tin, "
                "Mạng máy tính và Truyền thông, An toàn Thông tin, Kỹ thuật Máy tính, Công nghệ Phần mềm."
            ),
            "summary": "UIT thành lập năm 2006, là thành viên ĐHQG TP.HCM, trụ sở ở TP Thủ Đức, đào tạo các ngành CNTT.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "uit.edu.vn", "category": "gioi-thieu"},
        },
        {
            "title": "Câu lạc bộ và hoạt động sinh viên tại UIT",
            "url": "https://ctsv.uit.edu.vn/cau-lac-bo-sinh-vien",
            "data_source_id": source_map.get("ctsv.uit.edu.vn") and source_map["ctsv.uit.edu.vn"].id,
            "category_id": skill_cat.id if skill_cat else None,
            "group_name": "Hoạt động sinh viên",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["câu lạc bộ", "hoạt động", "sinh viên", "ngoại khóa"],
            "raw_content": (
                "UIT có nhiều câu lạc bộ và đội nhóm sinh viên hoạt động sôi nổi. "
                "Các CLB nổi bật bao gồm: CLB Lập trình UIT, CLB Robotics, CLB Multimedia, "
                "CLB English, CLB Vovinam, Đội tuyển ACM/ICPC, Đội tuyển Security (UIT Sec). "
                "Các sự kiện lớn hàng năm: Ngày hội Công nghệ Thông tin, UIT Hackathon, "
                "Hội thao sinh viên, Lễ khai giảng, Lễ tốt nghiệp."
            ),
            "cleaned_content": (
                "Câu lạc bộ và hoạt động sinh viên UIT:\n"
                "Câu lạc bộ kỹ thuật:\n"
                "- CLB Lập trình UIT: tổ chức workshop, hackathon và training cho sinh viên yêu lập trình\n"
                "- CLB Robotics UIT: nghiên cứu, chế tạo robot và tham gia các cuộc thi kỹ thuật\n"
                "- Đội tuyển ACM/ICPC: tuyển chọn và huấn luyện sinh viên lập trình thi đấu quốc gia/quốc tế\n"
                "- UIT Sec: CLB an toàn thông tin, tổ chức CTF và training về cybersecurity\n"
                "Câu lạc bộ văn hóa - thể thao:\n"
                "- CLB English: phát triển kỹ năng tiếng Anh giao tiếp và học thuật\n"
                "- CLB Multimedia: sản xuất nội dung, thiết kế đồ họa, video\n"
                "- CLB Vovinam, CLB Cầu lông, CLB Bóng đá\n"
                "Sự kiện hàng năm:\n"
                "- Ngày hội Công nghệ Thông tin UIT (thường vào tháng 4)\n"
                "- UIT Hackathon\n"
                "- Hội thao sinh viên ĐHQG-HCM\n"
                "- Lễ khai giảng (tháng 9)\n"
                "- Lễ tốt nghiệp (tháng 3-4 và tháng 9-10)"
            ),
            "summary": "UIT có nhiều CLB kỹ thuật (Lập trình, Robotics, ACM, UIT Sec) và văn hóa thể thao, cùng các sự kiện lớn hàng năm.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": False,
            "vector_metadata": {"source": "ctsv.uit.edu.vn", "category": "hoat-dong-sinh-vien"},
        },
        {
            "title": "Các phòng ban và đơn vị hành chính UIT",
            "url": "https://www.uit.edu.vn/don-vi-hanh-chinh",
            "data_source_id": source_map.get("uit.edu.vn") and source_map["uit.edu.vn"].id,
            "category_id": announcement_cat.id if announcement_cat else None,
            "group_name": "Giới thiệu trường",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["phòng ban", "đơn vị", "liên hệ", "UIT"],
            "raw_content": (
                "UIT có các phòng ban chính: Phòng Đào tạo Đại học (DAA), Phòng Công tác Sinh viên (CTSV), "
                "Phòng Kế hoạch Tài chính (KHTC), Phòng Quản trị, Phòng Tổ chức Hành chính, "
                "Văn phòng các Chương trình Đặc biệt (OEP). "
                "Các khoa: Khoa CNTT, Khoa KHMT, Khoa HTTT, Khoa Mạng máy tính và Truyền thông, "
                "Khoa Kỹ thuật Máy tính, Khoa Công nghệ Phần mềm."
            ),
            "cleaned_content": (
                "Các phòng ban và đơn vị tại UIT:\n"
                "Phòng ban hành chính:\n"
                "- Phòng Đào tạo Đại học (DAA): daa.uit.edu.vn - đầu mối học vụ, CTĐT, đăng ký học phần\n"
                "- Phòng Công tác Sinh viên (CTSV): ctsv.uit.edu.vn - học bổng, hỗ trợ sinh viên, tâm lý\n"
                "- Phòng Kế hoạch Tài chính (KHTC): khtc.uit.edu.vn - học phí, tài chính\n"
                "- Văn phòng Chương trình Đặc biệt (OEP): oep.uit.edu.vn - chương trình chất lượng cao\n"
                "Các khoa chuyên môn:\n"
                "- Khoa Công nghệ Thông tin: fit.uit.edu.vn\n"
                "- Khoa Khoa học Máy tính: cs.uit.edu.vn\n"
                "- Khoa Hệ thống Thông tin: httt.uit.edu.vn\n"
                "- Khoa Mạng máy tính và Truyền thông: nc.uit.edu.vn\n"
                "- Khoa Kỹ thuật Máy tính: fce.uit.edu.vn\n"
                "- Khoa Công nghệ Phần mềm: se.uit.edu.vn"
            ),
            "summary": "UIT có các phòng ban DAA, CTSV, KHTC, OEP và 6 khoa chuyên môn về CNTT và liên quan.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "uit.edu.vn", "category": "phong-ban"},
        },
        {
            "title": "Học bổng và hỗ trợ tài chính cho sinh viên UIT",
            "url": "https://ctsv.uit.edu.vn/hoc-bong",
            "data_source_id": source_map.get("ctsv.uit.edu.vn") and source_map["ctsv.uit.edu.vn"].id,
            "category_id": academic_cat.id if academic_cat else None,
            "group_name": "Học bổng",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["học bổng", "hỗ trợ tài chính", "CTSV"],
            "raw_content": (
                "UIT có nhiều chương trình học bổng dành cho sinh viên xuất sắc và sinh viên có hoàn cảnh khó khăn. "
                "Học bổng khuyến khích học tập được xét theo kết quả học tập từng học kỳ. "
                "Ngoài ra còn có học bổng từ doanh nghiệp và các tổ chức phi chính phủ."
            ),
            "cleaned_content": (
                "Học bổng và hỗ trợ tài chính tại UIT:\n"
                "1. Học bổng Khuyến khích Học tập (KKHT): xét theo kết quả học tập, GPA ≥ 3.2/4.0 (tùy loại)\n"
                "2. Học bổng Chính sách: dành cho sinh viên thuộc diện ưu tiên theo quy định nhà nước\n"
                "3. Học bổng Doanh nghiệp: do các công ty CNTT tài trợ (FPT, VNG, Viettel, Samsung, v.v.)\n"
                "4. Hỗ trợ sinh viên khó khăn: Phòng CTSV xét và hỗ trợ theo học kỳ\n"
                "5. Quỹ hỗ trợ sinh viên ĐHQG-HCM\n"
                "Để đăng ký học bổng, sinh viên nộp hồ sơ tại Phòng CTSV hoặc theo thông báo trên website. "
                "Thông tin chi tiết: https://ctsv.uit.edu.vn/hoc-bong"
            ),
            "summary": "UIT có học bổng KKHT, học bổng chính sách, học bổng doanh nghiệp và hỗ trợ sinh viên khó khăn từ Phòng CTSV.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "ctsv.uit.edu.vn", "category": "hoc-bong"},
        },
        {
            "title": "Quy chế đào tạo đại học theo tín chỉ tại UIT",
            "url": "https://daa.uit.edu.vn/quy-che-dao-tao",
            "data_source_id": source_map.get("daa.uit.edu.vn") and source_map["daa.uit.edu.vn"].id,
            "category_id": academic_cat.id if academic_cat else None,
            "group_name": "Quy chế học vụ",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["quy chế", "tín chỉ", "cảnh báo học vụ", "buộc thôi học", "điều kiện tốt nghiệp"],
            "raw_content": (
                "UIT áp dụng quy chế đào tạo đại học theo hệ thống tín chỉ của ĐHQG-HCM. "
                "Sinh viên có thể bị cảnh báo học vụ nếu GPA học kỳ < 1.0 hoặc GPA tích lũy thấp hơn quy định. "
                "Điều kiện tốt nghiệp bao gồm: hoàn thành đủ số tín chỉ theo CTĐT, GPA tích lũy ≥ 2.0/4.0, "
                "đạt chuẩn ngoại ngữ (thường TOEIC 450 hoặc tương đương), không có môn chưa hoàn thành."
            ),
            "cleaned_content": (
                "Quy chế học vụ tại UIT (hệ thống tín chỉ):\n"
                "Thang điểm: 4.0 (A=4.0, B+=3.5, B=3.0, C+=2.5, C=2.0, D+=1.5, D=1.0, F=0)\n"
                "Cảnh báo học vụ:\n"
                "- GPA học kỳ < 1.0: bị cảnh báo\n"
                "- GPA tích lũy < ngưỡng quy định theo năm học\n"
                "- Tích lũy quá ít tín chỉ so với lộ trình\n"
                "Buộc thôi học: bị cảnh báo học vụ 2 lần liên tiếp hoặc 3 lần trong toàn khóa học.\n"
                "Điều kiện tốt nghiệp:\n"
                "- Hoàn thành đủ số tín chỉ theo CTĐT (thường 120-150 tín chỉ tùy ngành)\n"
                "- GPA tích lũy ≥ 2.0/4.0\n"
                "- Đạt chuẩn ngoại ngữ theo quy định (TOEIC 450 hoặc tương đương)\n"
                "- Không có môn học nợ điểm\n"
                "- Hoàn thành nghĩa vụ tài chính (học phí, v.v.)\n"
                "Thông tin đầy đủ tại: https://daa.uit.edu.vn/quy-che-dao-tao"
            ),
            "summary": "UIT dùng tín chỉ thang 4.0, cảnh báo học vụ khi GPA thấp, điều kiện tốt nghiệp gồm GPA ≥ 2.0 và chuẩn ngoại ngữ.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "daa.uit.edu.vn", "category": "quy-che"},
        },
        {
            "title": "Hỗ trợ tâm lý sinh viên UIT - Không gian Chia sẻ",
            "url": "https://ctsv.uit.edu.vn/ho-tro-tam-ly",
            "data_source_id": source_map.get("ctsv.uit.edu.vn") and source_map["ctsv.uit.edu.vn"].id,
            "category_id": wellbeing_cat.id if wellbeing_cat else None,
            "group_name": "Hỗ trợ tâm lý",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["tâm lý", "hỗ trợ", "stress", "không gian chia sẻ", "CTSV"],
            "raw_content": (
                "Phòng CTSV tổ chức Không gian Chia sẻ tại phòng A104, hỗ trợ sinh viên khi gặp áp lực học tập, "
                "khó khăn tâm lý, hoặc cần lắng nghe và tư vấn ban đầu. "
                "Không cần đặt lịch trước, sinh viên có thể đến trực tiếp trong giờ hành chính. "
                "Email hỗ trợ: ctsv@uit.edu.vn"
            ),
            "cleaned_content": (
                "Hỗ trợ tâm lý sinh viên UIT:\n"
                "Không gian Chia sẻ UIT:\n"
                "- Địa điểm: Phòng A104, cơ sở UIT\n"
                "- Hình thức: lắng nghe, tư vấn ban đầu, kết nối chuyên gia khi cần\n"
                "- Không yêu cầu đặt lịch trước (giờ hành chính)\n"
                "- Email: ctsv@uit.edu.vn\n"
                "Nếu sinh viên đang gặp áp lực lớn, khó khăn tinh thần hoặc cần hỗ trợ khẩn cấp:\n"
                "- Liên hệ trực tiếp Phòng CTSV\n"
                "- Đường dây hỗ trợ sức khỏe tâm thần quốc gia: 1800 599 920 (miễn phí)\n"
                "- Trong trường hợp khẩn cấp: gọi 115 hoặc đến cơ sở y tế gần nhất"
            ),
            "summary": "Phòng CTSV có Không gian Chia sẻ tại A104 hỗ trợ tâm lý ban đầu cho sinh viên, liên hệ ctsv@uit.edu.vn.",
            "confidence_level": ConfidenceLevel.HIGH,
            "is_official_uit": True,
            "is_wellbeing_related": True,
            "vector_metadata": {"source": "ctsv.uit.edu.vn", "category": "tam-ly"},
        },
        {
            "title": "Lịch học kỳ và sự kiện học vụ năm học 2025-2026 UIT",
            "url": "https://daa.uit.edu.vn/lich-hoc-ky-2025-2026",
            "data_source_id": source_map.get("daa.uit.edu.vn") and source_map["daa.uit.edu.vn"].id,
            "category_id": academic_cat.id if academic_cat else None,
            "group_name": "Lịch học vụ",
            "published_at": now,
            "updated_source_at": now,
            "tags": ["lịch học kỳ", "2025-2026", "học vụ", "khai giảng", "tốt nghiệp"],
            "raw_content": (
                "Năm học 2025-2026 tại UIT bao gồm học kỳ 1 (tháng 9/2025 - tháng 1/2026), "
                "học kỳ 2 (tháng 2/2026 - tháng 6/2026) và học kỳ hè (tháng 7-8/2026). "
                "Lễ khai giảng thường tổ chức vào đầu tháng 10. Xét tốt nghiệp HK2 dự kiến tháng 4/2026."
            ),
            "cleaned_content": (
                "Lịch học kỳ năm học 2025-2026 UIT (dự kiến):\n"
                "Học kỳ 1 (HK1 2025-2026):\n"
                "- Bắt đầu: tháng 9/2025\n"
                "- Kết thúc: tháng 1/2026\n"
                "- Lễ khai giảng: đầu tháng 10/2025\n"
                "Học kỳ 2 (HK2 2025-2026):\n"
                "- Bắt đầu: tháng 2/2026\n"
                "- Kết thúc: tháng 6/2026\n"
                "- Xét tốt nghiệp dự kiến: tháng 4/2026\n"
                "- Lễ tốt nghiệp: tháng 9-10/2026\n"
                "Học kỳ Hè (HKH 2025-2026):\n"
                "- Thời gian: tháng 7 - tháng 8/2026\n"
                "Lịch cụ thể có thể thay đổi, sinh viên theo dõi thông báo chính thức tại daa.uit.edu.vn."
            ),
            "summary": "Năm học 2025-2026: HK1 tháng 9/2025-1/2026, HK2 tháng 2-6/2026, xét tốt nghiệp HK2 tháng 4/2026.",
            "confidence_level": ConfidenceLevel.MEDIUM,
            "is_official_uit": True,
            "is_academic_related": True,
            "vector_metadata": {"source": "daa.uit.edu.vn", "category": "lich-hoc-ky"},
        },
    ]

    for doc_data in extra_docs:
        existing = db.query(CollectedDocument).filter(CollectedDocument.url == doc_data["url"]).first()
        if existing is None and (doc_data.get("vector_metadata") or {}).get("category") == "ban-giam-hieu":
            existing = db.query(CollectedDocument).filter(CollectedDocument.url == "https://www.uit.edu.vn/gioi-thieu/ban-giam-hieu").first()
        if existing is None:
            db.add(CollectedDocument(**doc_data))
            continue
        for key, value in doc_data.items():
            setattr(existing, key, value)
    db.flush()


def seed(db: Session) -> None:
    source_map = upsert_default_sources(db)
    upsert_default_system_configs(db)
    _, student, _ = upsert_default_accounts(db)
    profile_map = {item.student_id: item for item in db.query(StudentProfile).all()}
    seed_advisor_demo_data(db, profile_map)
    now = datetime.now(timezone.utc)
    seed_student_schedules(db, profile_map, now)
    upsert_uit_knowledge_docs(db, source_map)
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
