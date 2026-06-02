"""add study_plans, study_plan_semesters, study_plan_courses tables

Revision ID: 002_study_plans
Revises: 001_initial
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002_study_plans"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="Kế hoạch học tập"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_graduation_year", sa.Integer(), nullable=True),
        sa.Column("total_required_credits", sa.Integer(), nullable=False, server_default="130"),
        sa.Column("max_credits_per_semester", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])

    op.create_table(
        "study_plan_semesters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_credits", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("plan_id", "label", name="uq_plan_semester_label"),
    )
    op.create_index("ix_study_plan_semesters_plan_id", "study_plan_semesters", ["plan_id"])

    op.create_table(
        "study_plan_courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("semester_id", sa.Integer(), sa.ForeignKey("study_plan_semesters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_code", sa.String(30), nullable=False),
        sa.Column("course_name", sa.String(255), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("category", sa.String(60), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("gpa_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("semester_id", "course_code", name="uq_plan_course_code"),
    )
    op.create_index("ix_study_plan_courses_semester_id", "study_plan_courses", ["semester_id"])


def downgrade() -> None:
    op.drop_table("study_plan_courses")
    op.drop_table("study_plan_semesters")
    op.drop_table("study_plans")
