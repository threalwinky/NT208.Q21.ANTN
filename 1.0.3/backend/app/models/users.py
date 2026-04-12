from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    student_profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False)


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    faculty: Mapped[str] = mapped_column(String(120), nullable=False)
    major: Mapped[str] = mapped_column(String(120), nullable=False)
    class_name: Mapped[str] = mapped_column(String(30), nullable=False)
    cohort: Mapped[str] = mapped_column(String(20), nullable=False)
    advisor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped[User] = relationship(back_populates="student_profile")
    academic_profile: Mapped["StudentAcademicProfile | None"] = relationship(back_populates="student_profile", uselist=False)
