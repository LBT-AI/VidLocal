"""add AI metadata fields to video_jobs

Revision ID: 003
Revises: 002
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: str = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("transcript", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("transcript_language", sa.String(10), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_title", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_description", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_tags", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_hashtags", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_hook", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("ai_category", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("risk_flags", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("metadata_status", sa.String(20), nullable=False, server_default="pending"))


def downgrade() -> None:
    op.drop_column("video_jobs", "transcript")
    op.drop_column("video_jobs", "transcript_language")
    op.drop_column("video_jobs", "ai_title")
    op.drop_column("video_jobs", "ai_description")
    op.drop_column("video_jobs", "ai_tags")
    op.drop_column("video_jobs", "ai_hashtags")
    op.drop_column("video_jobs", "ai_summary")
    op.drop_column("video_jobs", "ai_hook")
    op.drop_column("video_jobs", "ai_category")
    op.drop_column("video_jobs", "risk_flags")
    op.drop_column("video_jobs", "metadata_status")
