from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    title: Mapped[str] = mapped_column(String(256), index=True)
    company: Mapped[str | None] = mapped_column(String(256), index=True)
    location: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text())
    source: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    normalized: Mapped[dict | None] = mapped_column(JSONB())
    embedding_id: Mapped[str | None] = mapped_column(String(128))
    semantic_score: Mapped[float | None] = mapped_column(Float(), index=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
