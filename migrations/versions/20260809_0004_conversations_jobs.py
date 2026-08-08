"""Add durable conversations and generation jobs.

Revision ID: 20260809_0004
Revises: 20260809_0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260809_0004"
down_revision = "20260809_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("current_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "thread_id"),
    )
    op.create_index(op.f("ix_conversations_owner_id"), "conversations", ["owner_id"])
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generation_jobs_conversation_id"),
        "generation_jobs",
        ["conversation_id"],
    )
    op.create_index(
        op.f("ix_generation_jobs_owner_id"), "generation_jobs", ["owner_id"]
    )
    op.create_index(op.f("ix_generation_jobs_status"), "generation_jobs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_index(op.f("ix_generation_jobs_owner_id"), table_name="generation_jobs")
    op.drop_index(
        op.f("ix_generation_jobs_conversation_id"), table_name="generation_jobs"
    )
    op.drop_table("generation_jobs")
    op.drop_index(op.f("ix_conversations_owner_id"), table_name="conversations")
    op.drop_table("conversations")
