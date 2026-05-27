from __future__ import annotations

from pydantic import BaseModel, Field


class GpaCourseInput(BaseModel):
    course_code: str | None = None
    name: str | None = None
    credits: int = Field(ge=0, le=20)
    grade: str | None = None
    numeric_grade: float | None = Field(default=None, ge=0, le=10)


class GpaCourseResult(BaseModel):
    course_code: str | None = None
    name: str | None = None
    credits: int
    grade: str | None = None
    numeric_grade: float | None = None
    counted: bool


class GpaCalculationRequest(BaseModel):
    courses: list[GpaCourseInput]


class GpaCalculationOut(BaseModel):
    total_credits: int
    counted_credits: int
    gpa: float | None = None
    rows: list[GpaCourseResult]


class GpaSimulationRequest(BaseModel):
    planned_courses: list[GpaCourseInput]


class GpaSimulationOut(BaseModel):
    semester_gpa: float | None = None
    projected_cumulative_gpa: float | None = None
    existing_counted_credits: int
    planned_counted_credits: int
    note: str


class GpaHistoryTermOut(BaseModel):
    semester_code: str
    credits: int
    gpa: float | None = None
    courses: list[GpaCourseResult]
