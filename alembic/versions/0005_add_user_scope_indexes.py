from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_add_user_scope_indexes"
down_revision = "0004_create_rag_evaluations"
branch_labels = None
depends_on = None


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _has_index("job_postings", "ix_job_postings_user_id"):
        op.create_index("ix_job_postings_user_id", "job_postings", ["user_id"])
    if not _has_index("applications", "ix_applications_user_id"):
        op.create_index("ix_applications_user_id", "applications", ["user_id"])


def downgrade() -> None:
    if _has_index("applications", "ix_applications_user_id"):
        op.drop_index("ix_applications_user_id", table_name="applications")
    if _has_index("job_postings", "ix_job_postings_user_id"):
        op.drop_index("ix_job_postings_user_id", table_name="job_postings")
