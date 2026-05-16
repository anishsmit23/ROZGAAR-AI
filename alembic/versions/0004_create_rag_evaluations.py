"""Create rag_evaluations table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_create_rag_evaluations"
down_revision = "0003_add_failed_application_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("context_precision", sa.Float(), nullable=True),
        sa.Column("context_recall", sa.Float(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rag_evaluations_user_id", "rag_evaluations", ["user_id"])
    op.create_index("ix_rag_evaluations_evaluated_at", "rag_evaluations", ["evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_rag_evaluations_evaluated_at", table_name="rag_evaluations")
    op.drop_index("ix_rag_evaluations_user_id", table_name="rag_evaluations")
    op.drop_table("rag_evaluations")
