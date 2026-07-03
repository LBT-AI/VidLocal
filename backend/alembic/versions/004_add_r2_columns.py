"""add R2 storage columns to video_jobs

Revision ID: 004
Revises: 003
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: str = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("r2_key", sa.Text(), nullable=True))
    op.add_column("video_jobs", sa.Column("r2_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("video_jobs", sa.Column("r2_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "r2_expires_at")
    op.drop_column("video_jobs", "r2_uploaded_at")
    op.drop_column("video_jobs", "r2_key")
