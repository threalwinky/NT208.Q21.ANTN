from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StudyDocumentOut(BaseModel):
    id: int
    title: str
    group_name: str | None = None
    url: str
    summary: str | None = None
    is_official_uit: bool
    updated_source_at: datetime | None = None
    tags: list[str] = []


class AcademicEventOut(BaseModel):
    id: int
    title: str
    group_name: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ClassScheduleOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    lecturer_name: str | None = None
    room_name: str | None = None
    weekday: int
    period_start: int
    period_end: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ExamScheduleOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    room_name: str | None = None
    exam_type: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None


class TaskRequest(BaseModel):
    title: str
    description: str | None = None
    task_type: str
    priority: str = "MEDIUM"
    due_at: datetime | None = None
    start_at: datetime | None = None
    is_recurring: bool = False
    recurring_rule: str | None = None
    remind_at: datetime | None = None
    reminder_message: str | None = None


class ReminderOut(BaseModel):
    id: int
    remind_at: datetime
    channel: str
    message: str | None = None
    sent: bool


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    task_type: str
    status: str
    priority: str
    due_at: datetime | None = None
    is_recurring: bool
    recurring_rule: str | None = None
    reminders: list[ReminderOut] = []


# ── Study Plan schemas ──────────────────────────────────────────────────────

class StudyPlanCourseRequest(BaseModel):
    course_code: str
    course_name: str
    credits: int = 3
    category: str | None = None
    is_required: bool = True
    note: str | None = None


class StudyPlanCourseOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credits: int
    category: str | None = None
    is_required: bool
    note: str | None = None


class StudyPlanSemesterRequest(BaseModel):
    label: str
    sort_order: int = 0
    max_credits: int = 24
    notes: str | None = None


class StudyPlanSemesterOut(BaseModel):
    id: int
    label: str
    sort_order: int
    max_credits: int
    total_credits: int
    notes: str | None = None
    courses: list[StudyPlanCourseOut] = []


class StudyPlanRequest(BaseModel):
    name: str = "Kế hoạch học tập"
    description: str | None = None
    target_graduation_year: int | None = None
    total_required_credits: int = 130
    max_credits_per_semester: int = 24


class StudyPlanOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    target_graduation_year: int | None = None
    total_required_credits: int
    max_credits_per_semester: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    semesters: list[StudyPlanSemesterOut] = []


class ValidationIssue(BaseModel):
    severity: str  # error | warning
    code: str
    message: str
    course_code: str | None = None
    semester_label: str | None = None


class StudyPlanValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = []
    total_planned_credits: int
    accumulated_unique_credits: int
    graduation_progress_pct: float

