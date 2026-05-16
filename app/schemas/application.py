from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApplicationCreateResponse(BaseModel):
    application_id: str
    task_id: str


class ResumeCustomizeRequest(BaseModel):
    job_id: UUID


class EmailGenerateRequest(BaseModel):
    application_id: UUID


class ApplicationStageUpdate(BaseModel):
    stage: str
    note: str | None = None


class ApplicationRead(BaseModel):
    id: UUID
    job_posting_id: UUID
    state: str
    stage_number: int
    resume_version_path: str | None = None
    email_draft: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
