from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.academic import ClassSchedule, ExamSchedule, Task
from app.models.knowledge import Announcement
from app.models.users import User
from app.models.wellbeing import MoodJournal
from app.schemas.dashboard import DashboardAnnouncement, DashboardOverview, DashboardScheduleItem, DashboardTask
from app.services.wellbeing_service import WellbeingService

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DashboardOverview:
    now = datetime.now(timezone.utc)
    wellbeing_service = WellbeingService()
    announcements = (
        db.query(Announcement)
        .order_by(Announcement.is_featured.desc(), Announcement.published_at.desc().nullslast())
        .limit(5)
        .all()
    )
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user.id, Task.status != "DONE")
        .order_by(Task.due_at.asc().nulls_last())
        .limit(6)
        .all()
    )
    profile_id = user.student_profile.id if user.student_profile else None
    classes = (
        db.query(ClassSchedule)
        .filter((ClassSchedule.student_profile_id == profile_id) | (ClassSchedule.student_profile_id.is_(None)))
        .order_by(ClassSchedule.starts_at.asc().nulls_last())
        .limit(4)
        .all()
    )
    exams = (
        db.query(ExamSchedule)
        .filter((ExamSchedule.student_profile_id == profile_id) | (ExamSchedule.student_profile_id.is_(None)))
        .filter(ExamSchedule.starts_at >= now)
        .order_by(ExamSchedule.starts_at.asc())
        .limit(2)
        .all()
    )
    latest_mood = (
        db.query(MoodJournal)
        .filter(MoodJournal.user_id == user.id, MoodJournal.is_soft_deleted.is_(False))
        .order_by(MoodJournal.created_at.desc())
        .first()
    )
    latest_analysis = wellbeing_service.analyze_energy(latest_mood.mood_state if latest_mood else None, latest_mood.short_note if latest_mood else None)
    insight = await wellbeing_service.build_insight(db, user)

    schedule_items = [
        DashboardScheduleItem(
            title=item.course_name,
            item_type="LỊCH HỌC",
            starts_at=item.starts_at or now,
            ends_at=item.ends_at,
            location=item.room_name,
        )
        for item in classes
        if item.starts_at
    ]
    schedule_items.extend(
        [
            DashboardScheduleItem(
                title=item.course_name,
                item_type="LỊCH THI",
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                location=item.room_name,
            )
            for item in exams
        ]
    )

    return DashboardOverview(
        announcements=[
            DashboardAnnouncement(
                id=item.id,
                title=item.title,
                group_name=item.group_name,
                published_at=item.published_at,
                url=item.url,
            )
            for item in announcements
        ],
        upcoming_tasks=[
            DashboardTask(
                id=item.id,
                title=item.title,
                task_type=item.task_type,
                due_at=item.due_at,
                status=item.status,
                priority=item.priority,
            )
            for item in tasks
        ],
        today_schedule=schedule_items,
        mood_label=latest_mood.mood_state.display_name if latest_mood and latest_mood.mood_state else None,
        latest_energy_level=latest_analysis.level,
        latest_energy_label=latest_analysis.label,
        energy_summary=insight["summary"],
        energy_trend=insight["trend"],
        metrics={
            "totalAnnouncements": db.query(Announcement).count(),
            "openTasks": db.query(Task).filter(Task.user_id == user.id, Task.status != "DONE").count(),
            "upcomingExams": db.query(ExamSchedule).filter(ExamSchedule.starts_at >= now).count(),
            "moodCheckins": db.query(MoodJournal).filter(MoodJournal.user_id == user.id).count(),
        },
    )
