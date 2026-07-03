"""add job_type and path fields to video_jobs

Revision ID: 005
Revises: 004
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: str = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("temp_dir", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("source_file_path", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("watermarked_file_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "watermarked_file_path")
    op.drop_column("video_jobs", "source_file_path")
    op.drop_column("video_jobs", "temp_dir")
