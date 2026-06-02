from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.v1.deps import get_current_user, get_db, require_admin
from app.api.v1.endpoints import feedback
from app.db.base import Base
from app.models.users import User, UserRole


def make_app():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(username="student", password_hash="x", full_name="Sinh viên UIT", role=UserRole.STUDENT)
    admin = User(username="admin", password_hash="x", full_name="Quản trị", role=UserRole.ADMIN)
    db.add_all([user, admin])
    db.commit()
    db.refresh(user)
    db.refresh(admin)

    app = FastAPI()
    app.include_router(feedback.router, prefix="/feedback")
    app.include_router(feedback.admin_router, prefix="/admin/feedback")

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: admin
    return app, db


def test_feedback_create_and_admin_update() -> None:
    app, db = make_app()
    try:
        client = TestClient(app)

        created = client.post("/feedback", json={"target_type": "chat", "rating": 5, "message": "Câu trả lời hữu ích."})
        assert created.status_code == 200
        feedback_id = created.json()["id"]

        listed = client.get("/admin/feedback")
        assert listed.status_code == 200
        assert listed.json()[0]["message"] == "Câu trả lời hữu ích."

        updated = client.put(f"/admin/feedback/{feedback_id}", json={"status": "RESOLVED", "is_resolved": True})
        assert updated.status_code == 200
        assert updated.json()["is_resolved"] is True
    finally:
        db.close()
