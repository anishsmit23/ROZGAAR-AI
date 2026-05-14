from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class JobSearchRequest(BaseModel):
    query: str
    location: str | None = None
    remote: bool = False
    limit: int = 25


class PipelineStartRequest(JobSearchRequest):
    pass


class PipelineStartResponse(BaseModel):
    task_id: str
    run_id: str


class JobRead(BaseModel):
    id: uuid.UUID
    title: str
    company: str | None = None
    location: str | None = None
    source: str | None = None
    source_url: str | None = None
    semantic_score: float | None = None
    discovered_at: datetime | None = None

    model_config = {"from_attributes": True}
