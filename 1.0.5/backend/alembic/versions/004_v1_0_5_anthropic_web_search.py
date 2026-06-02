"""v1.0.5: Anthropic API + Web Search + fixes

Revision ID: 004_v1_0_5
Revises: 003_spotify_oauth
Create Date: 2026-05-13

Thay đổi chính trong v1.0.5:
- Chuyển MiMo provider sang Anthropic /v1/messages format
- Thêm web search tool (DuckDuckGo)
- Bật streaming mặc định
- Fix DB connection pooling
- Fix spotify.py secret_key → jwt_secret
- Thêm structured logging
"""
from __future__ import annotations

from alembic import op


revision = "004_v1_0_5"
down_revision = "003_spotify_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Không thay đổi schema – tất cả là infrastructure/service changes
    pass


def downgrade() -> None:
    pass
