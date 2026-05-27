from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.users import StudentProfile, User
from app.schemas.profile import ProfileOut, ProfileUpdateRequest

router = APIRouter()


def serialize_profile(user: User) -> ProfileOut:
    profile = user.student_profile
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return ProfileOut(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=role,
        student_profile_id=profile.id if profile else None,
        student_id=profile.student_id if profile else None,
        faculty=profile.faculty if profile else None,
        major=profile.major if profile else None,
        class_name=profile.class_name if profile else None,
        cohort=profile.cohort if profile else None,
        advisor_name=profile.advisor_name if profile else None,
    )


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)) -> ProfileOut:
    return serialize_profile(user)


@router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    if payload.full_name is not None:
        value = payload.full_name.strip()
        if not value:
            raise HTTPException(status_code=400, detail="Họ tên không được để trống.")
        user.full_name = value
    if payload.email is not None:
        user.email = payload.email.strip() or None

    profile_values = {
        "student_id": payload.student_id,
        "faculty": payload.faculty,
        "major": payload.major,
        "class_name": payload.class_name,
        "cohort": payload.cohort,
        "advisor_name": payload.advisor_name,
    }
    has_profile_update = any(value is not None for value in profile_values.values())

    if user.student_profile:
        for key, value in profile_values.items():
            if value is not None:
                setattr(user.student_profile, key, value.strip() if isinstance(value, str) else value)
    elif has_profile_update:
        required = ["student_id", "faculty", "major", "class_name", "cohort"]
        missing = [key for key in required if not profile_values.get(key)]
        if missing:
            raise HTTPException(status_code=400, detail="Cần đủ MSSV, khoa, ngành, lớp và khóa để tạo hồ sơ sinh viên.")
        db.add(
            StudentProfile(
                user_id=user.id,
                student_id=payload.student_id or "",
                faculty=payload.faculty or "",
                major=payload.major or "",
                class_name=payload.class_name or "",
                cohort=payload.cohort or "",
                advisor_name=payload.advisor_name,
            )
        )

    db.commit()
    db.refresh(user)
    return serialize_profile(user)
