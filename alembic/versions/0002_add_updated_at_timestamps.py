"""Add updated_at timestamps to agent_runs and job_postings tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_updated_at_timestamps"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at column to agent_runs table."""
    op.add_column(
        "agent_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    """Add updated_at column to job_postings table."""
    op.add_column(
        "job_postings",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove updated_at column from job_postings table."""
    op.drop_column("job_postings", "updated_at")

    """Remove updated_at column from agent_runs table."""
    op.drop_column("agent_runs", "updated_at")
