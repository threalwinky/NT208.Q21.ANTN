from __future__ import annotations

from enum import Enum

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class CourseCategory(str, Enum):
    FOUNDATION = "FOUNDATION"
    CORE = "CORE"
    ELECTIVE = "ELECTIVE"
    THESIS = "THESIS"
    ENGLISH = "ENGLISH"
    GENERAL = "GENERAL"


class PrerequisiteType(str, Enum):
    REQUIRED = "REQUIRED"
    COREQUISITE = "COREQUISITE"
    RECOMMENDED = "RECOMMENDED"


class CourseRecordStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    WITHDRAWN = "WITHDRAWN"
    WAIVED = "WAIVED"


class SemesterPlanStatus(str, Enum):
    DRAFT = "DRAFT"
    RECOMMENDED = "RECOMMENDED"
    LOCKED = "LOCKED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DegreeProgram(Base, TimestampMixin):
    __tablename__ = "degree_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty: Mapped[str] = mapped_column(String(150), nullable=False)
    major: Mapped[str] = mapped_column(String(150), nullable=False)
    cohort_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_required_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=130)
    elective_required_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    english_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    academic_profiles: Mapped[list["StudentAcademicProfile"]] = relationship(back_populates="program")
    requirements: Mapped[list["ProgramCourseRequirement"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
    )


class DegreeCourse(Base, TimestampMixin):
    __tablename__ = "degree_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default=CourseCategory.CORE.value)
    department_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    requirements: Mapped[list["ProgramCourseRequirement"]] = relationship(back_populates="course")
    prerequisite_links: Mapped[list["CoursePrerequisite"]] = relationship(
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    prerequisite_for_links: Mapped[list["CoursePrerequisite"]] = relationship(
        foreign_keys="CoursePrerequisite.prerequisite_course_id",
        back_populates="prerequisite_course",
        cascade="all, delete-orphan",
    )
    records: Mapped[list["StudentCourseRecord"]] = relationship(back_populates="course")


class ProgramCourseRequirement(Base, TimestampMixin):
    __tablename__ = "program_course_requirements"
    __table_args__ = (UniqueConstraint("program_id", "course_id", name="uq_program_requirement_course"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("degree_programs.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("degree_courses.id", ondelete="CASCADE"), nullable=False)
    recommended_semester: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    requirement_group: Mapped[str] = mapped_column(String(60), nullable=False, default="Cốt lõi")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped["DegreeProgram"] = relationship(back_populates="requirements")
    course: Mapped["DegreeCourse"] = relationship(back_populates="requirements")


class CoursePrerequisite(Base, TimestampMixin):
    __tablename__ = "course_prerequisites"
    __table_args__ = (UniqueConstraint("course_id", "prerequisite_course_id", name="uq_course_prerequisite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("degree_courses.id", ondelete="CASCADE"), nullable=False)
    prerequisite_course_id: Mapped[int] = mapped_column(ForeignKey("degree_courses.id", ondelete="CASCADE"), nullable=False)
    prerequisite_type: Mapped[str] = mapped_column(String(30), nullable=False, default=PrerequisiteType.REQUIRED.value)
    minimum_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    course: Mapped["DegreeCourse"] = relationship(
        foreign_keys=[course_id],
        back_populates="prerequisite_links",
    )
    prerequisite_course: Mapped["DegreeCourse"] = relationship(
        foreign_keys=[prerequisite_course_id],
        back_populates="prerequisite_for_links",
    )


class StudentAcademicProfile(Base, TimestampMixin):
    __tablename__ = "student_academic_profiles"
    __table_args__ = (UniqueConstraint("student_profile_id", name="uq_academic_profile_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    program_id: Mapped[int] = mapped_column(ForeignKey("degree_programs.id"), nullable=False)
    cohort_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cohort_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expected_graduation_term: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_semester_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_credits_per_term: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    cumulative_gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    student_profile: Mapped["StudentProfile"] = relationship(back_populates="academic_profile")
    program: Mapped["DegreeProgram"] = relationship(back_populates="academic_profiles")
    course_records: Mapped[list["StudentCourseRecord"]] = relationship(
        back_populates="academic_profile",
        cascade="all, delete-orphan",
    )
    semester_plans: Mapped[list["SemesterPlan"]] = relationship(
        back_populates="academic_profile",
        cascade="all, delete-orphan",
    )
    risk_snapshots: Mapped[list["AcademicRiskSnapshot"]] = relationship(
        back_populates="academic_profile",
        cascade="all, delete-orphan",
    )


class StudentCourseRecord(Base, TimestampMixin):
    __tablename__ = "student_course_records"
    __table_args__ = (UniqueConstraint("academic_profile_id", "course_id", "semester_code", name="uq_student_course_semester"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_profile_id: Mapped[int] = mapped_column(ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("degree_courses.id"), nullable=False)
    semester_code: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CourseRecordStatus.PLANNED.value)
    letter_grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    numeric_grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    academic_profile: Mapped["StudentAcademicProfile"] = relationship(back_populates="course_records")
    course: Mapped["DegreeCourse"] = relationship(back_populates="records")


class SemesterPlan(Base, TimestampMixin):
    __tablename__ = "semester_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_profile_id: Mapped[int] = mapped_column(ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    semester_code: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SemesterPlanStatus.RECOMMENDED.value)
    max_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    academic_profile: Mapped["StudentAcademicProfile"] = relationship(back_populates="semester_plans")
    items: Mapped[list["SemesterPlanItem"]] = relationship(back_populates="semester_plan", cascade="all, delete-orphan")


class SemesterPlanItem(Base, TimestampMixin):
    __tablename__ = "semester_plan_items"
    __table_args__ = (UniqueConstraint("semester_plan_id", "course_id", name="uq_plan_item_course"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_plan_id: Mapped[int] = mapped_column(ForeignKey("semester_plans.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("degree_courses.id"), nullable=False)
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    planning_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    semester_plan: Mapped["SemesterPlan"] = relationship(back_populates="items")
    course: Mapped["DegreeCourse"] = relationship()


class AcademicRiskSnapshot(Base, TimestampMixin):
    __tablename__ = "academic_risk_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_profile_id: Mapped[int] = mapped_column(ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default=RiskLevel.LOW.value)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    signals_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recommendations_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    academic_profile: Mapped["StudentAcademicProfile"] = relationship(back_populates="risk_snapshots")
