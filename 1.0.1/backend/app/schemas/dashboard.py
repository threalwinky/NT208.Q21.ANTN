from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardAnnouncement(BaseModel):
    id: int
    title: str
    group_name: str
    published_at: datetime | None = None
    url: str


class DashboardTask(BaseModel):
    id: int
    title: str
    task_type: str
    due_at: datetime | None = None
    status: str
    priority: str


class DashboardScheduleItem(BaseModel):
    title: str
    item_type: str
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = None


class DashboardOverview(BaseModel):
    announcements: list[DashboardAnnouncement]
    upcoming_tasks: list[DashboardTask]
    today_schedule: list[DashboardScheduleItem]
    mood_label: str | None = None
    latest_energy_level: int = 3
    latest_energy_label: str = "Trung bình"
    energy_summary: str = ""
    energy_trend: str = "STABLE"
    metrics: dict[str, int]
