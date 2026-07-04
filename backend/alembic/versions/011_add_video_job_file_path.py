"""add file_path to video_jobs

Revision ID: 011
Revises: 010
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011"
down_revision: str = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("video_jobs", sa.Column("file_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "file_path")
