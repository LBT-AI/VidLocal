"""add thumbnail fields to video_jobs

Revision ID: 008
Revises: 007
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: str = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("thumbnail_prompts", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("thumbnail_path", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("thumbnail_status", sa.String(20), nullable=False, server_default="pending"))


def downgrade() -> None:
    op.drop_column("video_jobs", "thumbnail_status")
    op.drop_column("video_jobs", "thumbnail_path")
    op.drop_column("video_jobs", "thumbnail_prompts")
