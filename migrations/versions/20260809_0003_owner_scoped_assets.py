"""Add owner-scoped templates and layout DNA.

Revision ID: 20260809_0003
Revises: 20260809_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260809_0003"
down_revision = "20260809_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name"),
    )
    op.create_index(op.f("ix_templates_owner_id"), "templates", ["owner_id"])
    op.create_table(
        "layout_dnas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name"),
    )
    op.create_index(op.f("ix_layout_dnas_owner_id"), "layout_dnas", ["owner_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_layout_dnas_owner_id"), table_name="layout_dnas")
    op.drop_table("layout_dnas")
    op.drop_index(op.f("ix_templates_owner_id"), table_name="templates")
    op.drop_table("templates")
