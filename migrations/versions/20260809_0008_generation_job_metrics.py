"""Record durable latency and failure metrics for generation jobs.

Revision ID: 20260809_0008
Revises: 20260809_0007
"""

import sqlalchemy as sa
from alembic import op

revision = "20260809_0008"
down_revision = "20260809_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(sa.Column("failure_kind", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("metrics", sa.JSON(), nullable=True))
        batch_op.create_index(
            "ix_generation_jobs_failure_kind", ["failure_kind"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_index("ix_generation_jobs_failure_kind")
        batch_op.drop_column("metrics")
        batch_op.drop_column("finished_at")
        batch_op.drop_column("duration_ms")
        batch_op.drop_column("failure_kind")
