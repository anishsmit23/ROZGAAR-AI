from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.db.base import async_session
from app.db.models.rag_evaluation import RagEvaluation
from app.db.models.user import User
from app.deps import get_current_user

router = APIRouter()


class RagEvaluationRead(BaseModel):
    id: UUID
    user_id: UUID
    evaluated_at: datetime
    context_precision: float | None = None
    context_recall: float | None = None
    sample_size: int

    model_config = {"from_attributes": True}


@router.get("/evaluations/latest", response_model=RagEvaluationRead)
async def get_latest_evaluation(user: User = Depends(get_current_user)) -> RagEvaluationRead:
    stmt = (
        select(RagEvaluation)
        .where(RagEvaluation.user_id == user.id)
        .order_by(RagEvaluation.evaluated_at.desc())
        .limit(1)
    )
    async with async_session() as session:
        result = await session.execute(stmt)
        evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation found")

    return evaluation
