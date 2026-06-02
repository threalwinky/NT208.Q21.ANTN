from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.academic import StudyPlan, StudyPlanCourse, StudyPlanSemester
from app.models.advisor import CoursePrerequisite, DegreeCourse
from app.models.users import User
from app.schemas.planner import (
    StudyPlanCourseOut,
    StudyPlanCourseRequest,
    StudyPlanOut,
    StudyPlanRequest,
    StudyPlanSemesterOut,
    StudyPlanSemesterRequest,
    StudyPlanValidationResult,
    ValidationIssue,
)

router = APIRouter()

MAX_CREDITS_PER_SEMESTER = 24
MIN_CREDITS_PER_SEMESTER = 0


def _serialize_course(c: StudyPlanCourse) -> StudyPlanCourseOut:
    return StudyPlanCourseOut(
        id=c.id,
        course_code=c.course_code,
        course_name=c.course_name,
        credits=c.credits,
        category=c.category,
        is_required=c.is_required,
        note=c.note,
    )


def _serialize_semester(s: StudyPlanSemester) -> StudyPlanSemesterOut:
    return StudyPlanSemesterOut(
        id=s.id,
        label=s.label,
        sort_order=s.sort_order,
        max_credits=s.max_credits,
        total_credits=s.total_credits,
        notes=s.notes,
        courses=[_serialize_course(c) for c in s.courses],
    )


def _serialize_plan(plan: StudyPlan) -> StudyPlanOut:
    return StudyPlanOut(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        target_graduation_year=plan.target_graduation_year,
        total_required_credits=plan.total_required_credits,
        max_credits_per_semester=plan.max_credits_per_semester,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        semesters=[_serialize_semester(s) for s in plan.semesters],
    )


def _get_plan_or_404(plan_id: int, user_id: int, db: Session) -> StudyPlan:
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == user_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch học tập.")
    return plan


# ── Plan CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[StudyPlanOut])
def list_plans(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[StudyPlanOut]:
    plans = db.query(StudyPlan).filter(StudyPlan.user_id == user.id).order_by(StudyPlan.created_at.desc()).all()
    return [_serialize_plan(p) for p in plans]


@router.post("", response_model=StudyPlanOut, status_code=201)
def create_plan(payload: StudyPlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StudyPlanOut:
    plan = StudyPlan(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        target_graduation_year=payload.target_graduation_year,
        total_required_credits=payload.total_required_credits,
        max_credits_per_semester=payload.max_credits_per_semester,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.get("/{plan_id}", response_model=StudyPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StudyPlanOut:
    return _serialize_plan(_get_plan_or_404(plan_id, user.id, db))


@router.put("/{plan_id}", response_model=StudyPlanOut)
def update_plan(plan_id: int, payload: StudyPlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StudyPlanOut:
    plan = _get_plan_or_404(plan_id, user.id, db)
    plan.name = payload.name
    plan.description = payload.description
    plan.target_graduation_year = payload.target_graduation_year
    plan.total_required_credits = payload.total_required_credits
    plan.max_credits_per_semester = payload.max_credits_per_semester
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.delete("/{plan_id}", response_model=dict)
def delete_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    plan = _get_plan_or_404(plan_id, user.id, db)
    db.delete(plan)
    db.commit()
    return {"deleted": True}


# ── Semester CRUD ─────────────────────────────────────────────────────────────

@router.post("/{plan_id}/semesters", response_model=StudyPlanSemesterOut, status_code=201)
def add_semester(
    plan_id: int,
    payload: StudyPlanSemesterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudyPlanSemesterOut:
    plan = _get_plan_or_404(plan_id, user.id, db)
    existing_labels = {s.label for s in plan.semesters}
    if payload.label in existing_labels:
        raise HTTPException(status_code=409, detail=f"Học kỳ '{payload.label}' đã tồn tại trong kế hoạch này.")
    semester = StudyPlanSemester(
        plan_id=plan.id,
        label=payload.label,
        sort_order=payload.sort_order,
        max_credits=payload.max_credits,
        notes=payload.notes,
    )
    db.add(semester)
    db.commit()
    db.refresh(semester)
    return _serialize_semester(semester)


@router.delete("/{plan_id}/semesters/{semester_id}", response_model=dict)
def remove_semester(
    plan_id: int,
    semester_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    plan = _get_plan_or_404(plan_id, user.id, db)
    semester = db.query(StudyPlanSemester).filter(StudyPlanSemester.id == semester_id, StudyPlanSemester.plan_id == plan.id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Không tìm thấy học kỳ.")
    db.delete(semester)
    db.commit()
    return {"deleted": True}


# ── Course CRUD ───────────────────────────────────────────────────────────────

@router.post("/{plan_id}/semesters/{semester_id}/courses", response_model=StudyPlanCourseOut, status_code=201)
def add_course(
    plan_id: int,
    semester_id: int,
    payload: StudyPlanCourseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudyPlanCourseOut:
    plan = _get_plan_or_404(plan_id, user.id, db)
    semester = db.query(StudyPlanSemester).filter(StudyPlanSemester.id == semester_id, StudyPlanSemester.plan_id == plan.id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Không tìm thấy học kỳ.")

    existing = db.query(StudyPlanCourse).filter(
        StudyPlanCourse.semester_id == semester_id,
        StudyPlanCourse.course_code == payload.course_code.strip().upper(),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Môn {payload.course_code} đã có trong học kỳ này.")

    course = StudyPlanCourse(
        semester_id=semester_id,
        course_code=payload.course_code.strip().upper(),
        course_name=payload.course_name,
        credits=payload.credits,
        category=payload.category,
        is_required=payload.is_required,
        note=payload.note,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _serialize_course(course)


@router.delete("/{plan_id}/semesters/{semester_id}/courses/{course_code}", response_model=dict)
def remove_course(
    plan_id: int,
    semester_id: int,
    course_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    plan = _get_plan_or_404(plan_id, user.id, db)
    semester = db.query(StudyPlanSemester).filter(StudyPlanSemester.id == semester_id, StudyPlanSemester.plan_id == plan.id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Không tìm thấy học kỳ.")
    course = db.query(StudyPlanCourse).filter(
        StudyPlanCourse.semester_id == semester_id,
        StudyPlanCourse.course_code == course_code.strip().upper(),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học trong học kỳ.")
    db.delete(course)
    db.commit()
    return {"deleted": True}


# ── Validation ────────────────────────────────────────────────────────────────

@router.post("/{plan_id}/validate", response_model=StudyPlanValidationResult)
def validate_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StudyPlanValidationResult:
    plan = _get_plan_or_404(plan_id, user.id, db)
    issues: list[ValidationIssue] = []

    all_course_codes: set[str] = set()
    seen_codes: set[str] = set()
    total_credits = 0
    unique_credits = 0

    prerequisite_map: dict[str, list[str]] = {}
    db_courses = db.query(DegreeCourse).all()
    for dc in db_courses:
        prereqs = [link.prerequisite_course.code for link in dc.prerequisite_links if link.prerequisite_course]
        if prereqs:
            prerequisite_map[dc.code] = prereqs

    for semester in plan.semesters:
        semester_credits = semester.total_credits
        if semester_credits > semester.max_credits:
            issues.append(ValidationIssue(
                severity="error",
                code="too_many_credits",
                message=f"Học kỳ '{semester.label}' có {semester_credits} tín chỉ, vượt giới hạn {semester.max_credits}.",
                semester_label=semester.label,
            ))

        for course in semester.courses:
            code = course.course_code
            total_credits += course.credits

            if code in seen_codes:
                issues.append(ValidationIssue(
                    severity="error",
                    code="repeated_course",
                    message=f"Môn {code} xuất hiện nhiều lần trong kế hoạch.",
                    course_code=code,
                    semester_label=semester.label,
                ))
            else:
                seen_codes.add(code)
                unique_credits += course.credits

            all_course_codes.add(code)

    codes_before: set[str] = set()
    for semester in plan.semesters:
        for course in semester.courses:
            code = course.course_code
            prereqs = prerequisite_map.get(code, [])
            for prereq in prereqs:
                if prereq not in codes_before:
                    issues.append(ValidationIssue(
                        severity="error",
                        code="missing_prerequisite",
                        message=f"Môn {code} yêu cầu tiên quyết {prereq} nhưng chưa được đăng ký trước đó.",
                        course_code=code,
                        semester_label=semester.label,
                    ))
        for course in semester.courses:
            codes_before.add(course.course_code)

    progress_pct = round(unique_credits / plan.total_required_credits * 100, 1) if plan.total_required_credits > 0 else 0.0
    if progress_pct < 100:
        remaining = plan.total_required_credits - unique_credits
        issues.append(ValidationIssue(
            severity="warning",
            code="graduation_credit_progress",
            message=f"Kế hoạch còn thiếu {remaining} tín chỉ để đủ điều kiện tốt nghiệp ({plan.total_required_credits} tín chỉ yêu cầu).",
        ))

    english_related = {"IT001", "IT002", "IT003", "ENG001", "ENG002"}
    has_english = any(c in all_course_codes for c in english_related)
    if not has_english:
        issues.append(ValidationIssue(
            severity="warning",
            code="missing_english_requirement",
            message="Kế hoạch chưa có môn tiếng Anh hoặc chứng chỉ tiếng Anh đầu ra. Hãy kiểm tra chuẩn đầu ra ngoại ngữ của chương trình đào tạo.",
        ))

    errors = [i for i in issues if i.severity == "error"]
    return StudyPlanValidationResult(
        valid=len(errors) == 0,
        issues=issues,
        total_planned_credits=total_credits,
        accumulated_unique_credits=unique_credits,
        graduation_progress_pct=progress_pct,
    )
