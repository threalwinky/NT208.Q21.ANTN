from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.wellbeing import InAppNotification
from app.models.users import User

router = APIRouter()


class NotificationOut(BaseModel):
    id: int
    title: str
    content: str
    is_read: bool
    action_link: str | None = None
    created_at: str


def _serialize(n: InAppNotification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        title=n.title,
        content=n.content,
        is_read=n.is_read,
        action_link=n.action_link,
        created_at=n.created_at.isoformat(),
    )


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[NotificationOut]:
    items = (
        db.query(InAppNotification)
        .filter(InAppNotification.user_id == user.id)
        .order_by(InAppNotification.created_at.desc())
        .limit(50)
        .all()
    )
    return [_serialize(n) for n in items]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    count = db.query(InAppNotification).filter(
        InAppNotification.user_id == user.id,
        InAppNotification.is_read.is_(False),
    ).count()
    return {"unread": count}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    notification = db.query(InAppNotification).filter(
        InAppNotification.id == notification_id,
        InAppNotification.user_id == user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")
    notification.is_read = True
    db.commit()
    return {"updated": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    updated = (
        db.query(InAppNotification)
        .filter(InAppNotification.user_id == user.id, InAppNotification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return {"updated": updated}
