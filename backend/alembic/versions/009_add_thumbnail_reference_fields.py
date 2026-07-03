"""add thumbnail reference fields to video_jobs

Revision ID: 009
Revises: 008
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: str = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("thumbnail_reference_frames", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("selected_thumbnail_reference", sa.Integer(), nullable=True))
    op.add_column("video_jobs", sa.Column("thumbnail_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "thumbnail_prompt")
    op.drop_column("video_jobs", "selected_thumbnail_reference")
    op.drop_column("video_jobs", "thumbnail_reference_frames")
