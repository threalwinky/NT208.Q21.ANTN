from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.advisor import (
    CourseRecordStatus,
    DegreeCourse,
    DegreeProgram,
    ProgramCourseRequirement,
    StudentAcademicProfile,
    StudentCourseRecord,
)
from app.models.chat import ChatMessage, ChatSession
from app.models.knowledge import CollectedDocument, ConfidenceLevel
from app.models.users import StudentProfile, User, UserRole
from app.services.chat_service import ChatService
from app.services.query_classifier import analyze_query
from app.services.rag_service import RetrievedContext


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_chat_history(db):
    user = User(
        username="24522045",
        password_hash="hashed",
        full_name="Vo Quang Vu",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(user)
    db.flush()

    session = ChatSession(user_id=user.id, title="Tư vấn chuẩn đầu ra", mode="STUDIFY")
    db.add(session)
    db.flush()

    db.add_all(
        [
            ChatMessage(
                session_id=session.id,
                role="user",
                category="ACADEMIC",
                content="chuẩn đầu ra tiếng anh của trường là gì?",
            ),
            ChatMessage(
                session_id=session.id,
                role="assistant",
                category="ACADEMIC",
                content="Chuẩn đầu ra tiếng Anh phụ thuộc chương trình đào tạo.",
            ),
        ]
    )
    db.commit()
    db.refresh(session)
    return session


def seed_student_with_academic_profile(db) -> User:
    user = User(
        username="24522045",
        password_hash="hashed",
        full_name="Võ Quang Vũ",
        role=UserRole.STUDENT,
        is_active=True,
    )
    profile = StudentProfile(
        user=user,
        student_id="24522045",
        faculty="Khoa Khoa học Máy tính",
        major="Khoa học máy tính",
        class_name="KHMT2024",
        cohort="K2024",
    )
    program = DegreeProgram(
        code="KHMT2024",
        name="Khoa học máy tính khóa 2024",
        faculty="Khoa Khoa học Máy tính",
        major="Khoa học máy tính",
        cohort_year=2024,
        total_required_credits=130,
        english_requirement="TOEIC 4 kỹ năng hoặc tương đương",
    )
    completed_course = DegreeCourse(code="IT001", name="Nhập môn lập trình", credits=4, category="CORE")
    missing_course = DegreeCourse(code="CS112", name="Phân tích và thiết kế thuật toán", credits=4, category="CORE")
    academic = StudentAcademicProfile(
        student_profile=profile,
        program=program,
        cohort_year=2024,
        cumulative_gpa=3.21,
        current_gpa=3.4,
        expected_graduation_term="HK2 2027-2028",
    )
    db.add_all([user, profile, program, completed_course, missing_course, academic])
    db.flush()
    db.add_all(
        [
            ProgramCourseRequirement(program=program, course=completed_course, recommended_semester=1, is_required=True),
            ProgramCourseRequirement(program=program, course=missing_course, recommended_semester=4, is_required=True),
            StudentCourseRecord(
                academic_profile=academic,
                course=completed_course,
                semester_code="HK1-2024-2025",
                status=CourseRecordStatus.PASSED.value,
                letter_grade="A",
                numeric_grade=9.0,
            ),
        ]
    )
    db.commit()
    db.refresh(user)
    return user


def test_build_effective_query_keeps_previous_user_context_for_short_follow_up() -> None:
    db = make_session()
    try:
        service = ChatService()
        session = seed_chat_history(db)

        effective_query = service._build_effective_query(db, session, "IELTS là bao nhiêu?")

        assert "chuẩn đầu ra tiếng anh của trường là gì?" in effective_query
        assert "IELTS là bao nhiêu?" in effective_query
    finally:
        db.close()


def test_direct_answer_rules_cover_common_academic_topics() -> None:
    service = ChatService()

    rules = service._direct_answer_rules("đăng ký học phần và học phí học kỳ này như thế nào?")

    assert "cổng hoặc bước xác nhận ĐKHP" in rules
    assert "hạn đóng" in rules


def test_user_context_brief_contains_personal_academic_progress() -> None:
    db = make_session()
    try:
        service = ChatService()
        user = seed_student_with_academic_profile(db)

        brief = service._user_context_brief(db, user)

        assert brief is not None
        assert "Võ Quang Vũ" in brief
        assert "GPA tích lũy hiện tại: 3.21" in brief
        assert "Tín chỉ đã tích lũy: 4" in brief
        assert "Tín chỉ còn cần hoàn thành: 126" in brief
    finally:
        db.close()


def test_personal_academic_answer_uses_logged_in_student_profile() -> None:
    db = make_session()
    try:
        service = ChatService()
        user = seed_student_with_academic_profile(db)

        answer = service._personal_academic_answer(db, user, "mình còn bao nhiêu tín nữa để tốt nghiệp?")

        assert answer is not None
        assert "4/130 tín chỉ" in answer
        assert "126 tín chỉ" in answer
        assert "3.21" in answer
    finally:
        db.close()


def test_direct_answer_rules_cover_annual_plan_queries() -> None:
    service = ChatService()

    rules = service._direct_answer_rules("lịch nghỉ hè năm 2026 của trường thế nào?")

    assert "kế hoạch năm học hoặc nghỉ hè" in rules
    assert "không công bố một kỳ nghỉ hè toàn trường cố định" in rules
    assert "Không ước lượng số tuần hoặc số tháng nghỉ hè" in rules
    assert "Không kết thúc bằng lời mời mở rộng" in rules


def test_crisis_turn_uses_local_safe_response_without_retrieval() -> None:
    service = ChatService()
    analysis = analyze_query("Mình không muốn sống nữa")

    assert service._is_crisis_turn(analysis) is True
    assert service._should_use_retrieval(analysis, "Mình không muốn sống nữa") is False

    answer = service._crisis_answer()
    assert "giữ bạn an toàn" in answer
    assert "cấp cứu" in answer
    assert "không phải bác sĩ" in answer


def test_grounding_brief_prefers_matching_annual_plan_context() -> None:
    service = ChatService()
    plan_2025_2026 = CollectedDocument(
        title="Kế hoạch đào tạo năm học 2025-2026",
        url="https://daa.uit.edu.vn/sites/daa/files/uploads/pdtdh_bieu-do-ke-hoach-dao-tao-nam-hoc-2025-2026-ver-4-2.jpg",
        summary="HK2 thi trong tháng 6/2026, sau đó có khoảng trống đến đầu hoặc giữa tháng 7/2026 trước khi vào học kỳ hè.",
        cleaned_content="Kế hoạch đào tạo năm học 2025-2026.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
    )
    plan_2026_2027 = CollectedDocument(
        title="Kế hoạch đào tạo năm học 2026-2027",
        url="https://daa.uit.edu.vn/sites/daa/files/uploads/pdtdh_bieu_do_ke_hoach_dao_tao_nam_hoc_2026-2027-ver-5.jpg",
        summary="Học kỳ hè năm học 2026-2027 nằm chủ yếu từ giữa tháng 7/2027 đến giữa tháng 8/2027.",
        cleaned_content="Kế hoạch đào tạo năm học 2026-2027.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
    )

    brief = service._grounding_brief(
        [
            RetrievedContext(document=plan_2026_2027, excerpt=plan_2026_2027.summary or "", score=0.95),
            RetrievedContext(document=plan_2025_2026, excerpt=plan_2025_2026.summary or "", score=0.9),
        ],
        "lịch nghỉ hè năm 2026",
    )

    assert brief is not None
    assert "Kế hoạch đào tạo năm học 2025-2026" in brief
    assert brief.find("2025-2026") != -1
    assert brief.find("2026-2027") == -1 or brief.find("2025-2026") < brief.find("2026-2027")
    assert "Chỉ kết luận từ các dữ kiện UIT ở trên" in brief


def test_grounding_brief_highlights_khtc_for_tuition_queries() -> None:
    service = ChatService()
    tuition_notice = CollectedDocument(
        title="[2025-2026] Thông báo thu học phí HK2, NH 2025-2026 trình độ ĐTĐH",
        url="https://khtc.uit.edu.vn/content/2025-2026-thong-bao-thu-hoc-phi-hk2-nh-2025-2026-trinh-do-dtdh",
        summary="Đợt 1 đến 22/02/2026, đợt 2 từ 16/03/2026 đến 17/05/2026, tra cứu tại student.uit.edu.vn/tracuu/hocphi.",
        cleaned_content="Thông báo thu học phí HK2 của KHTC.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
    )
    faculty_notice = CollectedDocument(
        title="Thông tin học phí chương trình riêng của khoa",
        url="https://fit.uit.edu.vn/hoc-phi-chuong-trinh-rieng",
        summary="Thông tin tham khảo về học phí riêng của một chương trình.",
        cleaned_content="Thông tin tham khảo của khoa.",
        confidence_level=ConfidenceLevel.HIGH,
        is_official_uit=True,
    )

    brief = service._grounding_brief(
        [
            RetrievedContext(document=faculty_notice, excerpt=faculty_notice.summary or "", score=0.97),
            RetrievedContext(document=tuition_notice, excerpt=tuition_notice.summary or "", score=0.8),
        ],
        "thông tin học phí hk2 2025-2026",
    )

    assert brief is not None
    assert "[2025-2026] Thông báo thu học phí HK2, NH 2025-2026 trình độ ĐTĐH" in brief
    assert brief.find("thu học phí HK2") != -1
    assert brief.find("chương trình riêng của khoa") == -1 or brief.find("thu học phí HK2") < brief.find("chương trình riêng của khoa")
    assert "tách rõ hạn đóng, mức thu, chương trình và khóa áp dụng" in brief
