"""Persist versioned structured editor documents.

Revision ID: 20260809_0007
Revises: 20260809_0006
"""

import sqlalchemy as sa
from alembic import op

revision = "20260809_0007"
down_revision = "20260809_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("revisions") as batch_op:
        batch_op.add_column(sa.Column("document_json", sa.JSON(), nullable=True))
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("document_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("document_json")
    with op.batch_alter_table("revisions") as batch_op:
        batch_op.drop_column("document_json")
