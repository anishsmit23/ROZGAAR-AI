from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


application_state = sa.Enum(
    "DISCOVERED",
    "RANKED",
    "RESUME_CUSTOMIZED",
    "EMAIL_GENERATED",
    "APPLIED",
    "ACKNOWLEDGED",
    "INTERVIEW_SCHEDULED",
    "CLOSED",
    name="application_state",
    native_enum=False,
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE application_state AS ENUM (
                'DISCOVERED',
                'RANKED',
                'RESUME_CUSTOMIZED',
                'EMAIL_GENERATED',
                'APPLIED',
                'ACKNOWLEDGED',
                'INTERVIEW_SCHEDULED',
                'CLOSED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("full_name", sa.String(length=256)),
        sa.Column("skills", postgresql.JSONB()),
        sa.Column("experience_years", sa.Integer()),
        sa.Column("resume_path", sa.String(length=1024)),
        sa.Column("preferences", postgresql.JSONB()),
        sa.Column("resume_text", sa.Text()),
    )

    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(length=256), nullable=False, index=True),
        sa.Column("company", sa.String(length=256), index=True),
        sa.Column("location", sa.String(length=256)),
        sa.Column("description", sa.Text()),
        sa.Column("source", sa.String(length=64)),
        sa.Column("source_url", sa.String(length=2048)),
        sa.Column("normalized", postgresql.JSONB()),
        sa.Column("embedding_id", sa.String(length=128)),
        sa.Column("semantic_score", sa.Float(), index=True),
        sa.Column("content_hash", sa.String(length=128), index=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", application_state, nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resume_version_path", sa.Text()),
        sa.Column("email_draft", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_applications_state", "applications", ["state"])

    op.create_table(
        "application_stage_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("from_state", application_state),
        sa.Column("to_state", application_state, nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("graph_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("input_snapshot", postgresql.JSONB()),
        sa.Column("output_snapshot", postgresql.JSONB()),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("task_id", sa.String(length=128), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "agent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("step_name", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("agent_events")
    op.drop_table("agent_runs")
    op.drop_table("application_stage_transitions")
    op.drop_index("ix_applications_state", table_name="applications")
    op.drop_table("applications")
    op.drop_table("job_postings")
    op.drop_table("users")
    application_state.drop(op.get_bind(), checkfirst=True)
