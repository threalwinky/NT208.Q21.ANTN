from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.v1.deps import get_current_user
from app.core.security import SESSION_COOKIE_NAME, create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.models.users import User, UserRole


def make_app():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(username="24522045", password_hash="x", full_name="Sinh viên UIT", role=UserRole.STUDENT, is_active=True)
    db.add(user)
    db.commit()

    app = FastAPI()

    @app.get("/me")
    def me(current_user: User = Depends(get_current_user)) -> dict[str, str]:
        return {"username": current_user.username}

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    return app, db


def test_get_current_user_accepts_httponly_session_cookie() -> None:
    app, db = make_app()
    try:
        client = TestClient(app)
        token = create_access_token({"sub": "24522045", "role": UserRole.STUDENT.value})
        client.cookies.set(SESSION_COOKIE_NAME, token)

        response = client.get("/me")

        assert response.status_code == 200
        assert response.json()["username"] == "24522045"
    finally:
        db.close()
