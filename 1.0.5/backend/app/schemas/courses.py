from __future__ import annotations

from pydantic import BaseModel


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    credits: int
    category: str
    department_name: str | None = None
    description: str | None = None
    requirement_groups: list[str] = []
    recommended_semesters: list[int] = []
    prerequisite_codes: list[str] = []
    metadata_json: dict | None = None
