"""create character_glossary_drafts and character_glossary_items tables

Revision ID: 007
Revises: 006
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "007"
down_revision: str = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "character_glossary_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "character_glossary_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("category", sa.String(20), nullable=False, server_default="character"),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("target_name", sa.Text(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("family_clan", sa.Text(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("relationships", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("pronoun_style", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("video_jobs", sa.Column("glossary_status", sa.String(20), nullable=True))
    op.add_column("video_jobs", sa.Column("glossary_draft_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("video_jobs", "glossary_draft_id")
    op.drop_column("video_jobs", "glossary_status")
    op.drop_table("character_glossary_items")
    op.drop_table("character_glossary_drafts")
