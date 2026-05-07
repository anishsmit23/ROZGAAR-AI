from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatusResponse(BaseModel):
    """Response model for task status queries."""
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, etc.)")
    result: dict[str, Any] | None = Field(None, description="Task result payload if completed")
    error: str | None = Field(None, description="Error message if task failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc-123-def",
                "status": "SUCCESS",
                "result": {"application_id": "app-123", "status": "completed"},
                "error": None,
            }
        }


class AgentRunResponse(BaseModel):
    """Response model for agent run information."""
    run_id: str = Field(..., description="Agent run ID")
    user_id: str = Field(..., description="User ID")
    graph_name: str = Field(..., description="Name of the agent graph executed")
    status: str = Field(..., description="Run status (queued, running, completed, failed)")
    input_snapshot: dict[str, Any] | None = Field(None, description="Input parameters snapshot")
    output_snapshot: dict[str, Any] | None = Field(None, description="Output results snapshot")
    task_id: str | None = Field(None, description="Associated Celery task ID")
    latency_ms: int | None = Field(None, description="Execution time in milliseconds")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run-123",
                "user_id": "user-123",
                "graph_name": "ResumeTailoringGraph",
                "status": "completed",
                "input_snapshot": {"application_id": "app-123"},
                "output_snapshot": {"resume_path": "minio://generated-resumes/app-123.pdf"},
                "task_id": "task-123",
                "latency_ms": 5000,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
