"""Add names to revision checkpoints.

Revision ID: 20260809_0005
Revises: 20260809_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20260809_0005"
down_revision = "20260809_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("revisions") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("revisions") as batch_op:
        batch_op.drop_column("name")
