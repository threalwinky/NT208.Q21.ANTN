from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter()


def serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role.value,
        email=user.email,
        student_id=user.student_profile.student_id if user.student_profile else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai mã đăng nhập hoặc mật khẩu.")

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return TokenResponse(access_token=token, user=serialize_user(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return serialize_user(user)

