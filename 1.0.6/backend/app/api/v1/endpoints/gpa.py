from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.advisor import CourseRecordStatus, StudentCourseRecord
from app.models.users import User
from app.schemas.gpa import (
    GpaCalculationOut,
    GpaCalculationRequest,
    GpaCourseInput,
    GpaCourseResult,
    GpaHistoryTermOut,
    GpaSimulationOut,
    GpaSimulationRequest,
)

router = APIRouter()

GRADE_POINTS = {
    "A+": 10.0,
    "A": 9.0,
    "B+": 8.0,
    "B": 7.0,
    "C+": 6.5,
    "C": 5.5,
    "D+": 5.0,
    "D": 4.0,
    "F": 0.0,
}


def numeric_grade(item: GpaCourseInput) -> float | None:
    if item.numeric_grade is not None:
        return item.numeric_grade
    if item.grade:
        return GRADE_POINTS.get(item.grade.strip().upper())
    return None


def calculate_courses(courses: list[GpaCourseInput]) -> GpaCalculationOut:
    rows: list[GpaCourseResult] = []
    total_credits = sum(item.credits for item in courses)
    counted_credits = 0
    weighted_points = 0.0
    for item in courses:
        numeric = numeric_grade(item)
        counted = numeric is not None and item.credits > 0
        if counted:
            counted_credits += item.credits
            weighted_points += item.credits * float(numeric)
        rows.append(
            GpaCourseResult(
                course_code=item.course_code,
                name=item.name,
                credits=item.credits,
                grade=item.grade,
                numeric_grade=numeric,
                counted=counted,
            )
        )
    return GpaCalculationOut(
        total_credits=total_credits,
        counted_credits=counted_credits,
        gpa=round(weighted_points / counted_credits, 2) if counted_credits else None,
        rows=rows,
    )


def records_for_user(user: User) -> list[StudentCourseRecord]:
    academic_profile = user.student_profile.academic_profile if user.student_profile else None
    if academic_profile is None:
        return []
    return list(academic_profile.course_records)


@router.post("/calculate", response_model=GpaCalculationOut)
def calculate_gpa(payload: GpaCalculationRequest, _: User = Depends(get_current_user)) -> GpaCalculationOut:
    return calculate_courses(payload.courses)


@router.post("/simulate", response_model=GpaSimulationOut)
def simulate_gpa(
    payload: GpaSimulationRequest,
    user: User = Depends(get_current_user),
) -> GpaSimulationOut:
    planned = calculate_courses(payload.planned_courses)
    existing_records = [
        item
        for item in records_for_user(user)
        if item.numeric_grade is not None and item.course and item.status in {CourseRecordStatus.PASSED.value, CourseRecordStatus.FAILED.value}
    ]
    existing_credits = sum(item.course.credits for item in existing_records)
    existing_points = sum(item.course.credits * float(item.numeric_grade or 0) for item in existing_records)
    planned_points = sum((row.numeric_grade or 0) * row.credits for row in planned.rows if row.counted)
    total_credits = existing_credits + planned.counted_credits
    projected = round((existing_points + planned_points) / total_credits, 2) if total_credits else planned.gpa
    return GpaSimulationOut(
        semester_gpa=planned.gpa,
        projected_cumulative_gpa=projected,
        existing_counted_credits=existing_credits,
        planned_counted_credits=planned.counted_credits,
        note="Mô phỏng dùng thang 10 và chỉ tính môn có điểm hợp lệ.",
    )


@router.get("/history", response_model=list[GpaHistoryTermOut])
def gpa_history(user: User = Depends(get_current_user)) -> list[GpaHistoryTermOut]:
    grouped: dict[str, list[GpaCourseInput]] = defaultdict(list)
    for record in records_for_user(user):
        if not record.course:
            continue
        grouped[record.semester_code].append(
            GpaCourseInput(
                course_code=record.course.code,
                name=record.course.name,
                credits=record.course.credits,
                grade=record.letter_grade,
                numeric_grade=record.numeric_grade,
            )
        )
    history: list[GpaHistoryTermOut] = []
    for semester_code in sorted(grouped):
        calculated = calculate_courses(grouped[semester_code])
        history.append(
            GpaHistoryTermOut(
                semester_code=semester_code,
                credits=calculated.counted_credits,
                gpa=calculated.gpa,
                courses=calculated.rows,
            )
        )
    return history
