"""Add OAuth token columns to spotify_accounts

Revision ID: 003_spotify_oauth
Revises: 002_study_plans
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003_spotify_oauth"
down_revision = "002_study_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("spotify_accounts", sa.Column("access_token_enc", sa.Text(), nullable=True))
    op.add_column("spotify_accounts", sa.Column("refresh_token_enc", sa.Text(), nullable=True))
    op.add_column("spotify_accounts", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("spotify_accounts", "token_expires_at")
    op.drop_column("spotify_accounts", "refresh_token_enc")
    op.drop_column("spotify_accounts", "access_token_enc")
