from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from celery.result import AsyncResult
from starlette.responses import StreamingResponse
from sqlalchemy import select

from app.cache.redis import get_redis
from app.db.base import async_session
from app.db.models.agent_run import AgentRun
from app.db.models.application import Application
from app.db.models.user import User
from app.deps import get_current_user
from app.schemas.task import TaskStatusResponse
from app.tasks.celery_app import celery_app

router = APIRouter()
SSE_TIMEOUT_SECONDS = 120


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    payload = result.result if result.successful() else None
    error = str(result.result) if result.failed() else None
    application_id = None
    stage = None

    async with async_session() as session:
        run_result = await session.execute(
            select(AgentRun).where(AgentRun.task_id == task_id, AgentRun.user_id == user.id)
        )
        run = run_result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Task not found")

        output = run.output_snapshot or {}
        input_snapshot = run.input_snapshot or {}
        application_id = output.get("application_id") or input_snapshot.get("application_id")
        error = error or output.get("error")

        if application_id:
            try:
                app_result = await session.execute(
                    select(Application).where(
                        Application.id == UUID(str(application_id)),
                        Application.user_id == user.id,
                    )
                )
                application = app_result.scalar_one_or_none()
            except ValueError:
                application = None
            if application:
                stage = application.state.value if hasattr(application.state, "value") else str(application.state)
            else:
                stage = output.get("stage")

    return TaskStatusResponse(
        task_id=task_id,
        state=result.status,
        status=result.status,
        result=payload if isinstance(payload, dict) else None,
        error=error,
        application_id=application_id,
        stage=stage,
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_status(
    task_id: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async with async_session() as session:
        run_result = await session.execute(
            select(AgentRun).where(AgentRun.task_id == task_id, AgentRun.user_id == user.id)
        )
        if not run_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Task not found")

    channel = f"task:{task_id}:status"

    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            deadline = asyncio.get_running_loop().time() + SSE_TIMEOUT_SECONDS
            while True:
                if await request.is_disconnected():
                    break

                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    yield f"data: {json.dumps({'state': 'TIMEOUT'})}\n\n"
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(1.0, remaining),
                )
                if not message:
                    continue

                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                elif not isinstance(data, str):
                    data = json.dumps(data)

                yield f"data: {data}\n\n"
                deadline = asyncio.get_running_loop().time() + SSE_TIMEOUT_SECONDS
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
