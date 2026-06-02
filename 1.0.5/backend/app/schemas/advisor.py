from __future__ import annotations

from pydantic import BaseModel


class AdvisorIdentityOut(BaseModel):
    student_name: str
    student_id: str
    faculty: str
    major: str
    class_name: str
    cohort_label: str
    birth_year_hint: int | None = None
    expected_graduation_term: str | None = None


class AdvisorCourseStatusOut(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    category: str
    recommended_semester: int
    requirement_group: str
    status: str
    status_label: str
    letter_grade: str | None = None
    semester_code: str | None = None
    prerequisites: list[str] = []


class AuditCategoryProgressOut(BaseModel):
    category: str
    required_credits: int
    passed_credits: int
    remaining_credits: int


class DegreeAuditOut(BaseModel):
    identity: AdvisorIdentityOut
    program_name: str
    total_required_credits: int
    passed_credits: int
    in_progress_credits: int
    remaining_credits: int
    completion_percent: int
    english_requirement: str | None = None
    milestone_summary: str
    category_progress: list[AuditCategoryProgressOut]
    required_courses: list[AdvisorCourseStatusOut]
    missing_core_courses: list[str]


class PlanCourseOut(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    category: str
    planned_reason: str
    prerequisite_codes: list[str] = []


class SemesterPlanOut(BaseModel):
    title: str
    semester_code: str
    total_credits: int
    max_credits: int
    notes: str
    courses: list[PlanCourseOut]


class GraphNodeOut(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    recommended_semester: int
    category: str
    status: str
    plan_slot: int | None = None


class GraphEdgeOut(BaseModel):
    from_course_id: int
    to_course_id: int
    prerequisite_type: str


class SemesterPlanningOut(BaseModel):
    identity: AdvisorIdentityOut
    recommended_credit_load: int
    blocking_courses: list[str]
    semesters: list[SemesterPlanOut]
    graph_nodes: list[GraphNodeOut]
    graph_edges: list[GraphEdgeOut]


class AcademicRiskAlertOut(BaseModel):
    identity: AdvisorIdentityOut
    risk_level: str
    risk_score: int
    summary: str
    signals: list[str]
    recommendations: list[str]
    overdue_task_count: int
    failed_course_count: int
    current_gpa: float | None = None
    cumulative_gpa: float | None = None


class AdvisorOverviewOut(BaseModel):
    degree_audit: DegreeAuditOut
    semester_planning: SemesterPlanningOut
    academic_risk: AcademicRiskAlertOut
