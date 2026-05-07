from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    graph_name: Mapped[str] = mapped_column(String(128), index=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB())
    output_snapshot: Mapped[dict | None] = mapped_column(JSONB())
    status: Mapped[str] = mapped_column(String(32), index=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer())
    task_id: Mapped[str | None] = mapped_column(String(128), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
