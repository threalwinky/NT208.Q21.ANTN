from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.advisor import DegreeCourse
from app.models.users import User
from app.schemas.courses import CourseOut

router = APIRouter()


def serialize_course(course: DegreeCourse) -> CourseOut:
    requirement_groups: list[str] = []
    recommended_semesters: list[int] = []
    for requirement in course.requirements:
        if requirement.requirement_group not in requirement_groups:
            requirement_groups.append(requirement.requirement_group)
        if requirement.recommended_semester not in recommended_semesters:
            recommended_semesters.append(requirement.recommended_semester)
    prerequisite_codes = [link.prerequisite_course.code for link in course.prerequisite_links if link.prerequisite_course]
    return CourseOut(
        id=course.id,
        code=course.code,
        name=course.name,
        credits=course.credits,
        category=course.category,
        department_name=course.department_name,
        description=course.description,
        requirement_groups=requirement_groups,
        recommended_semesters=sorted(recommended_semesters),
        prerequisite_codes=prerequisite_codes,
        metadata_json=course.metadata_json,
    )


@router.get("", response_model=list[CourseOut])
def list_courses(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CourseOut]:
    query = db.query(DegreeCourse)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(DegreeCourse.code.ilike(pattern), DegreeCourse.name.ilike(pattern)))
    if category:
        query = query.filter(DegreeCourse.category == category.upper().strip())
    courses = query.order_by(DegreeCourse.code.asc()).limit(120).all()
    return [serialize_course(course) for course in courses]


@router.get("/{course_code}", response_model=CourseOut)
def get_course(
    course_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CourseOut:
    course = db.query(DegreeCourse).filter(DegreeCourse.code == course_code.upper().strip()).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học.")
    return serialize_course(course)
