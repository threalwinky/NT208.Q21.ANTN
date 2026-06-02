from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.feedback import UserFeedback
from app.models.users import User
from app.schemas.feedback import FeedbackCreateRequest, FeedbackOut, FeedbackUpdateRequest

router = APIRouter()
admin_router = APIRouter()


def serialize_feedback(item: UserFeedback) -> FeedbackOut:
    return FeedbackOut(
        id=item.id,
        user_id=item.user_id,
        user_name=item.user.full_name if item.user else "Sinh viên",
        target_type=item.target_type,
        target_id=item.target_id,
        rating=item.rating,
        message=item.message,
        status=item.status,
        admin_note=item.admin_note,
        is_resolved=item.is_resolved,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
    )


@router.post("", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FeedbackOut:
    item = UserFeedback(
        user_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        rating=payload.rating,
        message=payload.message,
        metadata_json=payload.metadata_json,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_feedback(item)


@router.get("/mine", response_model=list[FeedbackOut])
def my_feedback(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[FeedbackOut]:
    items = db.query(UserFeedback).filter(UserFeedback.user_id == user.id).order_by(UserFeedback.created_at.desc()).limit(30).all()
    return [serialize_feedback(item) for item in items]


@admin_router.get("", response_model=list[FeedbackOut])
def list_feedback(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[FeedbackOut]:
    items = db.query(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(80).all()
    return [serialize_feedback(item) for item in items]


@admin_router.put("/{feedback_id}", response_model=FeedbackOut)
def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FeedbackOut:
    item = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phản hồi.")
    if payload.status is not None:
        item.status = payload.status
    if payload.admin_note is not None:
        item.admin_note = payload.admin_note
    if payload.is_resolved is not None:
        item.is_resolved = payload.is_resolved
    db.commit()
    db.refresh(item)
    return serialize_feedback(item)
