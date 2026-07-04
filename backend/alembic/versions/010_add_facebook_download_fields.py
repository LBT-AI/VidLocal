"""add facebook download fields to video_jobs

Revision ID: 010
Revises: 009
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010"
down_revision: str = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("video_id", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("resolved_url", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("normalized_url", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("error_code", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "error_code")
    op.drop_column("video_jobs", "normalized_url")
    op.drop_column("video_jobs", "resolved_url")
    op.drop_column("video_jobs", "video_id")
