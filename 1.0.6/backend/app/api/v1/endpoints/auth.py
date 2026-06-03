from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import SESSION_COOKIE_NAME, create_access_token, verify_password
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


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    payload: LoginRequest = Body(...),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai mã đăng nhập hoặc mật khẩu.")

    token = create_access_token({"sub": user.username, "role": user.role.value})
    _set_session_cookie(response, token)
    return TokenResponse(access_token=token, user=serialize_user(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(response: Response, user: User = Depends(get_current_user)) -> TokenResponse:
    token = create_access_token({"sub": user.username, "role": user.role.value})
    _set_session_cookie(response, token)
    return TokenResponse(access_token=token, user=serialize_user(user))


@router.post("/logout", response_model=dict[str, bool])
def logout(response: Response) -> dict[str, bool]:
    _clear_session_cookie(response)
    return {"logged_out": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return serialize_user(user)
