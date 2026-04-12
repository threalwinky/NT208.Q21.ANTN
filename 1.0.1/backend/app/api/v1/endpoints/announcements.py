from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge import Announcement
from app.models.users import User
from app.models.wellbeing import SavedAnnouncement

router = APIRouter()


@router.get("")
def list_announcements(
    group_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    query = db.query(Announcement)
    if group_name:
        query = query.filter(Announcement.group_name == group_name)
    items = query.order_by(Announcement.is_featured.desc(), Announcement.published_at.desc().nullslast()).limit(30).all()
    saved = {
        item.announcement_id
        for item in db.query(SavedAnnouncement).filter(SavedAnnouncement.user_id == user.id).all()
    }
    return [
        {
            "id": item.id,
            "title": item.title,
            "shortDescription": item.short_description,
            "groupName": item.group_name,
            "url": item.url,
            "isFeatured": item.is_featured,
            "publishedAt": item.published_at,
            "isSaved": item.id in saved,
            "isOfficialUit": item.is_official_uit,
            "tags": item.tags or [],
        }
        for item in items
    ]


@router.post("/{announcement_id}/save")
def toggle_save_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    item = (
        db.query(SavedAnnouncement)
        .filter(SavedAnnouncement.user_id == user.id, SavedAnnouncement.announcement_id == announcement_id)
        .first()
    )
    if item:
        db.delete(item)
        db.commit()
        return {"isSaved": False}
    db.add(SavedAnnouncement(user_id=user.id, announcement_id=announcement_id))
    db.commit()
    return {"isSaved": True}

