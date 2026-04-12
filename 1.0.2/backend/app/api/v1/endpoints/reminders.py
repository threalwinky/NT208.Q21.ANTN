from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.academic import AcademicEvent, ClassSchedule, ExamSchedule, Reminder, Task, TaskStatus, normalize_task_status
from app.models.knowledge import CollectedDocument
from app.models.users import User
from app.schemas.planner import (
    AcademicEventOut,
    ClassScheduleOut,
    ExamScheduleOut,
    ReminderOut,
    StudyDocumentOut,
    TaskOut,
    TaskRequest,
)

router = APIRouter()


def serialize_task(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=normalize_task_status(task.status),
        priority=task.priority,
        due_at=task.due_at,
        is_recurring=task.is_recurring,
        recurring_rule=task.recurring_rule,
        reminders=[
            ReminderOut(
                id=reminder.id,
                remind_at=reminder.remind_at,
                channel=reminder.channel,
                message=reminder.message,
                sent=reminder.sent,
            )
            for reminder in task.reminders
        ],
    )


@router.get("/documents", response_model=list[StudyDocumentOut])
def list_documents(
    q: str | None = Query(default=None),
    group_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[StudyDocumentOut]:
    query = db.query(CollectedDocument).filter(CollectedDocument.is_academic_related.is_(True))
    if q:
        query = query.filter(CollectedDocument.title.ilike(f"%{q}%"))
    if group_name:
        query = query.filter(CollectedDocument.group_name == group_name)
    items = query.order_by(CollectedDocument.updated_source_at.desc().nullslast()).limit(20).all()
    return [
        StudyDocumentOut(
            id=item.id,
            title=item.title,
            group_name=item.group_name,
            url=item.url,
            summary=item.summary,
            is_official_uit=item.is_official_uit,
            updated_source_at=item.updated_source_at,
            tags=item.tags or [],
        )
        for item in items
    ]


@router.get("/events", response_model=list[AcademicEventOut])
def list_events(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[AcademicEventOut]:
    items = db.query(AcademicEvent).order_by(AcademicEvent.starts_at.asc().nullslast()).all()
    return [
        AcademicEventOut(
            id=item.id,
            title=item.title,
            group_name=item.group_name,
            description=item.description,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
        )
        for item in items
    ]


@router.get("/class-schedule", response_model=list[ClassScheduleOut])
def list_class_schedule(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ClassScheduleOut]:
    profile_id = user.student_profile.id if user.student_profile else None
    items = db.query(ClassSchedule).filter((ClassSchedule.student_profile_id == profile_id) | (ClassSchedule.student_profile_id.is_(None))).all()
    return [
        ClassScheduleOut(
            id=item.id,
            course_code=item.course_code,
            course_name=item.course_name,
            lecturer_name=item.lecturer_name,
            room_name=item.room_name,
            weekday=item.weekday,
            period_start=item.period_start,
            period_end=item.period_end,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
        )
        for item in items
    ]


@router.get("/exam-schedule", response_model=list[ExamScheduleOut])
def list_exam_schedule(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ExamScheduleOut]:
    profile_id = user.student_profile.id if user.student_profile else None
    items = db.query(ExamSchedule).filter((ExamSchedule.student_profile_id == profile_id) | (ExamSchedule.student_profile_id.is_(None))).all()
    return [
        ExamScheduleOut(
            id=item.id,
            course_code=item.course_code,
            course_name=item.course_name,
            room_name=item.room_name,
            exam_type=item.exam_type,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
        )
        for item in items
    ]


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TaskOut]:
    items = (
        db.query(Task)
        .filter(Task.user_id == user.id, Task.status != TaskStatus.DONE.value)
        .order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
        .all()
    )
    return [serialize_task(item) for item in items]


@router.post("/tasks", response_model=TaskOut)
def create_task(
    payload: TaskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskOut:
    task = Task(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        status=TaskStatus.OPEN.value,
        priority=payload.priority,
        due_at=payload.due_at,
        start_at=payload.start_at,
        is_recurring=payload.is_recurring,
        recurring_rule=payload.recurring_rule,
    )
    db.add(task)
    db.flush()
    if payload.remind_at:
        db.add(
            Reminder(
                task_id=task.id,
                remind_at=payload.remind_at,
                channel="IN_APP",
                message=payload.reminder_message or f"Nhắc việc: {payload.title}",
                recurring_mode=payload.recurring_rule if payload.is_recurring else None,
            )
        )
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.patch("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> TaskOut:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy việc cần làm.")
    task.status = TaskStatus.DONE.value
    db.commit()
    db.refresh(task)
    return serialize_task(task)
