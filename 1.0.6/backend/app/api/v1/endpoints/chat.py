from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.chat import ChatSession
from app.models.users import User
from app.schemas.chat import ChatMessageItem, ChatReply, ChatSessionOut, SendMessageRequest
from app.services.chat_service import ChatService

router = APIRouter()


def _session_mode(chat_mode: str) -> str:
    return "STUDIFY_EXTENDED" if chat_mode == "extended" else "STUDIFY_QUICK"


def serialize_session(session: ChatSession) -> ChatSessionOut:
    ordered_messages = sorted(session.messages, key=lambda item: (item.created_at, item.id))
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        mode=session.mode,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            ChatMessageItem(
                id=item.id,
                role=item.role,
                category=item.category,
                content=item.content,
                created_at=item.created_at,
                risk_score=item.risk_score,
                is_urgent=item.is_urgent,
            )
            for item in ordered_messages
        ],
    )


def _resolve_session(db: Session, user: User, session_id: int | None, content: str, session_mode: str) -> ChatSession:
    if session_id is None:
        session = ChatSession(user_id=user.id, title=content[:80], mode=session_mode)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    if session.mode != session_mode:
        session.mode = session_mode
        db.commit()
        db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ChatSessionOut]:
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc()).all()
    return [serialize_session(item) for item in sessions]


@router.delete("/sessions/{session_id}", response_model=dict[str, bool])
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, bool]:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    db.delete(session)
    db.commit()
    return {"deleted": True}


@router.post("/send", response_model=ChatReply)
async def send_message(
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatReply:
    session_mode = _session_mode(payload.chat_mode)
    session = _resolve_session(db, user, payload.session_id, payload.content, session_mode)
    return await ChatService().answer(db, session, payload.content, chat_mode=payload.chat_mode, user=user)


@router.post("/stream")
async def stream_message(
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    session_mode = _session_mode(payload.chat_mode)
    session = _resolve_session(db, user, payload.session_id, payload.content, session_mode)
    session_id = session.id
    user_id = user.id

    async def event_stream():
        stream_db = SessionLocal()
        try:
            stream_session = (
                stream_db.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
                .first()
            )
            stream_user = stream_db.query(User).filter(User.id == user_id).first()
            if not stream_session or not stream_user:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Không tìm thấy phiên chat.'}, ensure_ascii=False)}\n\n"
                return
            async for event in ChatService().stream_answer(stream_db, stream_session, payload.content, chat_mode=payload.chat_mode, user=stream_user):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            stream_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
