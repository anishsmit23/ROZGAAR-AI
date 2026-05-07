from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicationState(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    RANKED = "RANKED"
    RESUME_CUSTOMIZED = "RESUME_CUSTOMIZED"
    EMAIL_GENERATED = "EMAIL_GENERATED"
    APPLIED = "APPLIED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    CLOSED = "CLOSED"


class ApplicationStage(enum.IntEnum):
    DISCOVERED = 1
    RANKED = 2
    RESUME_CUSTOMIZED = 3
    EMAIL_GENERATED = 4
    APPLIED = 5
    ACKNOWLEDGED = 6
    INTERVIEW_SCHEDULED = 7
    CLOSED = 8


APPLICATION_STAGE_ORDER: dict[ApplicationState, int] = {
    ApplicationState.DISCOVERED: 1,
    ApplicationState.RANKED: 2,
    ApplicationState.RESUME_CUSTOMIZED: 3,
    ApplicationState.EMAIL_GENERATED: 4,
    ApplicationState.APPLIED: 5,
    ApplicationState.ACKNOWLEDGED: 6,
    ApplicationState.INTERVIEW_SCHEDULED: 7,
    ApplicationState.CLOSED: 8,
}


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_postings.id"))

    state: Mapped[ApplicationState] = mapped_column(Enum(ApplicationState, name="application_state"), index=True)
    stage_number: Mapped[int] = mapped_column(Integer(), default=1)
    resume_version_path: Mapped[str | None] = mapped_column(Text())
    email_draft: Mapped[str | None] = mapped_column(Text())

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ApplicationStageTransition(Base):
    __tablename__ = "application_stage_transitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    from_state: Mapped[ApplicationState | None] = mapped_column(Enum(ApplicationState, name="application_state"))
    to_state: Mapped[ApplicationState] = mapped_column(Enum(ApplicationState, name="application_state"))
    note: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
