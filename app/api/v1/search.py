from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db.base import async_session
from app.db.models.agent_run import AgentRun
from app.db.models.user import User
from app.deps import get_current_user
from app.schemas.job import PipelineStartRequest, PipelineStartResponse
from app.tasks.agent_tasks import run_job_search

router = APIRouter()


@router.post("/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(
    payload: PipelineStartRequest,
    user: User = Depends(get_current_user),
) -> PipelineStartResponse:
    async with async_session() as session:
        run = AgentRun(
            user_id=user.id,
            graph_name="JobSearchGraph",
            input_snapshot=payload.model_dump(),
            status="queued",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    task_result = run_job_search.delay(str(user.id), payload.model_dump(), str(run.id))

    async with async_session() as session:
        stmt = select(AgentRun).where(AgentRun.id == run.id)
        result = await session.execute(stmt)
        run = result.scalar_one()
        run.task_id = task_result.id
        await session.commit()

    return PipelineStartResponse(task_id=task_result.id, run_id=str(run.id))
