"""Add FAILED application state."""

from __future__ import annotations

from alembic import op

revision = "0003_add_failed_application_state"
down_revision = "0002_add_updated_at_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum
                WHERE enumlabel = 'FAILED'
                AND enumtypid = 'application_state'::regtype
            ) THEN
                ALTER TYPE application_state ADD VALUE 'FAILED';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL cannot safely remove enum values without rebuilding dependent
    # columns. Leave the value in place on downgrade.
    pass
