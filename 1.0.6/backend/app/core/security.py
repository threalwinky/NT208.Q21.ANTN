from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE_NAME = "studify_session"


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(payload: dict[str, Any], expires_minutes: int | None = None) -> str:
    settings = get_settings()
    to_encode = payload.copy()
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    to_encode.update({"exp": expire_at})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
