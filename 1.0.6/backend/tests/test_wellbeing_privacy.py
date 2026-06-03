from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.users import User, UserRole
from app.models.wellbeing import WellbeingNote


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_wellbeing_notes_are_private_by_default_and_soft_deleted() -> None:
    db = make_session()
    try:
        user = User(username="student", password_hash="x", full_name="Student", role=UserRole.STUDENT)
        db.add(user)
        db.flush()
        note = WellbeingNote(user_id=user.id, content="Mình cần ghi riêng vài dòng.")
        db.add(note)
        db.commit()
        db.refresh(note)

        assert note.is_private is True
        assert note.is_soft_deleted is False

        note.is_soft_deleted = True
        db.commit()

        visible = db.query(WellbeingNote).filter(WellbeingNote.user_id == user.id, WellbeingNote.is_soft_deleted.is_(False)).all()
        assert visible == []
    finally:
        db.close()
