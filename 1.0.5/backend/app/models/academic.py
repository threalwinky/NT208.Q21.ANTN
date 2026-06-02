from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    DONE = "DONE"


def normalize_task_status(status: str | None) -> str:
    if (status or "").upper() == TaskStatus.DONE.value:
        return TaskStatus.DONE.value
    return TaskStatus.OPEN.value


class AcademicEvent(Base, TimestampMixin):
    __tablename__ = "academic_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    group_name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ClassSchedule(Base, TimestampMixin):
    __tablename__ = "class_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_profile_id: Mapped[int | None] = mapped_column(ForeignKey("student_profiles.id"), nullable=True)
    course_code: Mapped[str] = mapped_column(String(30), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    lecturer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    display_color: Mapped[str | None] = mapped_column(String(20), nullable=True)


class ExamSchedule(Base, TimestampMixin):
    __tablename__ = "exam_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_profile_id: Mapped[int | None] = mapped_column(ForeignKey("student_profiles.id"), nullable=True)
    course_code: Mapped[str] = mapped_column(String(30), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    exam_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=TaskStatus.OPEN.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurring_rule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    suggested_source: Mapped[str | None] = mapped_column(String(120), nullable=True)

    reminders: Mapped[list["Reminder"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), default="IN_APP", nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurring_mode: Mapped[str | None] = mapped_column(String(120), nullable=True)

    task: Mapped["Task"] = relationship(back_populates="reminders")


class StudyPlan(Base, TimestampMixin):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Kế hoạch học tập")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_required_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=130)
    max_credits_per_semester: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    semesters: Mapped[list["StudyPlanSemester"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="StudyPlanSemester.sort_order"
    )


class StudyPlanSemester(Base, TimestampMixin):
    __tablename__ = "study_plan_semesters"
    __table_args__ = (UniqueConstraint("plan_id", "label", name="uq_plan_semester_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped["StudyPlan"] = relationship(back_populates="semesters")
    courses: Mapped[list["StudyPlanCourse"]] = relationship(
        back_populates="semester", cascade="all, delete-orphan"
    )

    @property
    def total_credits(self) -> int:
        return sum(c.credits for c in self.courses)


class StudyPlanCourse(Base, TimestampMixin):
    __tablename__ = "study_plan_courses"
    __table_args__ = (UniqueConstraint("semester_id", "course_code", name="uq_plan_course_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("study_plan_semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code: Mapped[str] = mapped_column(String(30), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    gpa_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    semester: Mapped["StudyPlanSemester"] = relationship(back_populates="courses")
