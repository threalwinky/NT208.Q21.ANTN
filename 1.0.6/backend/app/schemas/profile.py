from __future__ import annotations

from pydantic import BaseModel


class ProfileOut(BaseModel):
    user_id: int
    username: str
    full_name: str
    email: str | None = None
    role: str
    student_profile_id: int | None = None
    student_id: str | None = None
    faculty: str | None = None
    major: str | None = None
    class_name: str | None = None
    cohort: str | None = None
    advisor_name: str | None = None


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    student_id: str | None = None
    faculty: str | None = None
    major: str | None = None
    class_name: str | None = None
    cohort: str | None = None
    advisor_name: str | None = None
