from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge import Announcement, CollectedDocument
from app.models.users import User

router = APIRouter()


@router.get("")
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=12, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    pattern = f"%{q.strip()}%"
    documents = (
        db.query(CollectedDocument)
        .filter(or_(CollectedDocument.title.ilike(pattern), CollectedDocument.cleaned_content.ilike(pattern), CollectedDocument.summary.ilike(pattern)))
        .order_by(CollectedDocument.updated_source_at.desc().nullslast(), CollectedDocument.id.desc())
        .limit(limit)
        .all()
    )
    announcements = (
        db.query(Announcement)
        .filter(or_(Announcement.title.ilike(pattern), Announcement.short_description.ilike(pattern)))
        .order_by(Announcement.published_at.desc().nullslast(), Announcement.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "query": q,
        "documents": [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
                "group_name": item.group_name,
                "is_official_uit": item.is_official_uit,
                "updated_source_at": item.updated_source_at,
                "type": "document",
            }
            for item in documents
        ],
        "announcements": [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "summary": item.short_description,
                "group_name": item.group_name,
                "is_official_uit": item.is_official_uit,
                "published_at": item.published_at,
                "type": "announcement",
            }
            for item in announcements
        ],
    }
