from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.users import StudentProfile, User, UserRole
from app.models.wellbeing import MoodJournal, MoodState
from app.scripts.seed_advisor import seed_advisor_demo_data
from app.services.academic_advisor_service import AcademicAdvisorService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def create_student(db, username: str, full_name: str, faculty: str, major: str, class_name: str):
    user = User(username=username, password_hash="hashed", full_name=full_name, role=UserRole.STUDENT, is_active=True)
    db.add(user)
    db.flush()
    profile = StudentProfile(
        user_id=user.id,
        student_id=username,
        faculty=faculty,
        major=major,
        class_name=class_name,
        cohort="2022-2026",
        advisor_name="GV demo",
    )
    db.add(profile)
    db.flush()
    return user, profile


def seed_demo_environment(db):
    vu_user, vu_profile = create_student(db, "24522045", "Vo Quang Vu", "Khoa Khoa học Máy tính", "Khoa học Máy tính", "KHMT2022")
    tu_user, tu_profile = create_student(
        db,
        "24520033",
        "Dang Minh Tu",
        "Khoa Mạng máy tính và Truyền thông",
        "Mạng máy tính và Truyền thông dữ liệu",
        "MMT2022",
    )
    db.add_all(
        [
            MoodState(code="TIRED", display_name="Hoi met", intensity=3),
            MoodState(code="PRESSURED", display_name="Ap luc", intensity=2),
        ]
    )
    db.flush()
    pressured_state = db.query(MoodState).filter(MoodState.code == "PRESSURED").first()
    if pressured_state is not None:
        db.add(
            MoodJournal(
                user_id=tu_user.id,
                mood_state_id=pressured_state.id,
                short_note="Deadline do an va hoc lai dang don.",
                energy_level=2,
                needs_human_support=False,
            )
        )
    db.commit()
    seed_advisor_demo_data(
        db,
        {
            vu_profile.student_id: vu_profile,
            tu_profile.student_id: tu_profile,
        },
    )
    db.commit()
    return vu_user, tu_user


def test_degree_audit_identifies_missing_core_courses() -> None:
    db = make_session()
    try:
        vu_user, _ = seed_demo_environment(db)
        service = AcademicAdvisorService()

        audit = service.build_degree_audit(db, vu_user)

        assert audit.program_name == "Cử nhân Khoa học Máy tính"
        assert audit.completion_percent > 0
        assert "CS338" in audit.missing_core_courses
        assert any(item.code == "CS331" for item in audit.required_courses)
    finally:
        db.close()


def test_semester_planning_prioritizes_failed_or_blocking_courses() -> None:
    db = make_session()
    try:
        vu_user, _ = seed_demo_environment(db)
        service = AcademicAdvisorService()

        planning = service.build_semester_planning(db, vu_user)

        first_semester_codes = [item.code for item in planning.semesters[0].courses]
        assert "CS338" in first_semester_codes
        assert planning.recommended_credit_load >= 12
        assert any(edge.to_course_id for edge in planning.graph_edges)
    finally:
        db.close()


def test_academic_risk_alert_becomes_high_for_weaker_profile() -> None:
    db = make_session()
    try:
        _, tu_user = seed_demo_environment(db)
        service = AcademicAdvisorService()

        risk = service.build_academic_risk(db, tu_user)

        assert risk.risk_level in {"MEDIUM", "HIGH"}
        assert risk.failed_course_count >= 1
        assert risk.risk_score >= 35
        assert risk.recommendations
    finally:
        db.close()
