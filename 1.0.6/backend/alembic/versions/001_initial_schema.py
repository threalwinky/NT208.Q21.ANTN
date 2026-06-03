"""initial schema — create all tables from v1.0.4 baseline

Revision ID: 001_initial
Revises:
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration is a no-op because init_db() via create_all() was used in earlier
    # versions. When running on a fresh database, alembic stamp head should be run after
    # init_db() so Alembic tracks subsequent migrations correctly.
    #
    # For new deployments use: alembic upgrade head (which will run all migrations from here)
    pass


def downgrade() -> None:
    pass
