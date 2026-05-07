from __future__ import annotations

from fastapi import APIRouter
from celery.result import AsyncResult

from app.schemas.task import TaskStatusResponse
from app.tasks.celery_app import celery_app

router = APIRouter()


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    payload = result.result if result.successful() else None
    error = str(result.result) if result.failed() else None

    return TaskStatusResponse(
        task_id=task_id,
        status=result.status,
        result=payload if isinstance(payload, dict) else None,
        error=error,
    )
