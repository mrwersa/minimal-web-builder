"""Allow generation jobs to be cancelled.

Revision ID: 20260809_0009
Revises: 20260809_0008
"""

import sqlalchemy as sa
from alembic import op

revision = "20260809_0009"
down_revision = "20260809_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cancel_requested",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_column("cancel_requested")
