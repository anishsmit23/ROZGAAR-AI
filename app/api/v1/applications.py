from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.db.base import async_session
from app.db.models.application import (
    APPLICATION_STAGE_ORDER,
    Application,
    ApplicationStageTransition,
    ApplicationState,
)
from app.db.models.agent_run import AgentRun
from app.db.models.job_posting import JobPosting
from app.db.models.user import User
from app.deps import get_current_user
from app.storage.minio_client import get_presigned_url
from app.schemas.application import (
    ApplicationCreateResponse,
    ApplicationRead,
    ApplicationStageUpdate,
    EmailGenerateRequest,
    ResumeCustomizeRequest,
)
from app.tasks.agent_tasks import run_email_generation, run_resume_tailor

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_uuid(value: UUID | str, field_name: str) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {field_name} format") from exc


@router.get("/applications/{application_id}/resume/download")
async def download_application_resume(
    application_id: UUID,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    async with async_session() as session:
        result = await session.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user.id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if not application.resume_version_path:
            raise HTTPException(status_code=404, detail="Resume not found")

        download_url = await get_presigned_url(application.resume_version_path, expires_seconds=3600)

        return {"download_url": download_url}


@router.post("/resume/customize", response_model=ApplicationCreateResponse)
async def tailor_resume(
    payload: ResumeCustomizeRequest,
    user: User = Depends(get_current_user),
) -> ApplicationCreateResponse:
    """Generate customized resume for a specific job."""
    job_id = _parse_uuid(payload.job_id, "job_id")
    
    async with async_session() as session:
        job = await session.get(JobPosting, job_id)
        if not job or job.user_id != user.id:
            raise HTTPException(status_code=404, detail="Job not found")

        # Check if an application already exists for this job
        stmt = select(Application).where(
            (Application.user_id == user.id) & 
            (Application.job_posting_id == job_id)
        )
        result = await session.execute(stmt)
        existing_app = result.scalar_one_or_none()
        
        if existing_app:
            application = existing_app
            # Check if in valid state for resume customization
            if application.state in (ApplicationState.EMAIL_GENERATED, ApplicationState.APPLIED, 
                                    ApplicationState.ACKNOWLEDGED, ApplicationState.INTERVIEW_SCHEDULED, 
                                    ApplicationState.CLOSED):
                raise HTTPException(status_code=409, detail=f"Cannot customize resume - application is in {application.state} state")
        else:
            application = Application(
                user_id=user.id,
                job_posting_id=job.id,
                state=ApplicationState.DISCOVERED,
                stage_number=APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED],
            )
            session.add(application)
            await session.commit()
            await session.refresh(application)

        # Log state transition
        if application.state != ApplicationState.RESUME_CUSTOMIZED:
            session.add(
                ApplicationStageTransition(
                    application_id=application.id,
                    user_id=user.id,
                    from_state=application.state,
                    to_state=ApplicationState.RESUME_CUSTOMIZED,
                    note="Resume customization requested",
                )
            )
        
        run = AgentRun(
            user_id=user.id,
            graph_name="ResumeTailoringGraph",
            input_snapshot={"application_id": str(application.id), "job_id": str(job.id)},
            status="queued",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    try:
        task_result = run_resume_tailor.delay(str(user.id), str(application.id), str(run.id))
        
        async with async_session() as session:
            run = await session.get(AgentRun, run.id)
            if run:
                run.task_id = task_result.id
                await session.commit()
    except Exception as e:
        async with async_session() as session:
            persisted_run = await session.get(AgentRun, run.id)
            if persisted_run:
                persisted_run.status = "failed"
                persisted_run.output_snapshot = {"error": str(e)}
                await session.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue resume customization task: {str(e)}")

    return ApplicationCreateResponse(application_id=str(application.id), task_id=task_result.id)


@router.post("/email/generate", response_model=ApplicationCreateResponse)
async def generate_email(
    payload: EmailGenerateRequest,
    user: User = Depends(get_current_user),
) -> ApplicationCreateResponse:
    """Generate cold email for a specific application."""
    application_id = _parse_uuid(payload.application_id, "application_id")
    
    async with async_session() as session:
        application = await session.get(Application, application_id)
        if not application or application.user_id != user.id:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Allow email generation from RANKED or RESUME_CUSTOMIZED states
        valid_states = (ApplicationState.RANKED, ApplicationState.RESUME_CUSTOMIZED)
        if application.state not in valid_states:
            raise HTTPException(
                status_code=409, 
                detail=f"Cannot generate email - application is in {application.state} state. Valid states: {', '.join([s.value for s in valid_states])}"
            )

        run = AgentRun(
            user_id=user.id,
            graph_name="EmailGenerationGraph",
            input_snapshot={"application_id": str(application_id)},
            status="queued",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    try:
        task_result = run_email_generation.delay(str(user.id), str(application_id), str(run.id))
        
        async with async_session() as session:
            run = await session.get(AgentRun, run.id)
            if run:
                run.task_id = task_result.id
                await session.commit()
    except Exception as e:
        async with async_session() as session:
            run = await session.get(AgentRun, run.id)
            if run:
                run.status = "failed"
                run.output_snapshot = {"error": str(e)}
                await session.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue email generation task: {str(e)}")

    return ApplicationCreateResponse(application_id=str(application_id), task_id=task_result.id)


@router.get("/applications", response_model=list[ApplicationRead])
@router.get("/applications/", response_model=list[ApplicationRead])
async def list_applications(
    state: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
) -> list[ApplicationRead]:
    """List user's applications with optional filtering by state."""
    stmt = select(Application).where(Application.user_id == user.id)
    
    if state:
        try:
            app_state = ApplicationState(state.upper())
            stmt = stmt.where(Application.state == app_state)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid state: {state}. Valid states: {', '.join([s.value for s in ApplicationState])}")
    
    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)

    try:
        async with async_session() as session:
            result = await session.execute(stmt)
            applications = list(result.scalars().all())
            return applications
    except Exception as e:
        logger.error(f"Failed to list applications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve applications")


@router.patch("/applications/{application_id}/stage", response_model=ApplicationRead)
async def update_application_stage(
    application_id: UUID,
    payload: ApplicationStageUpdate,
    user: User = Depends(get_current_user),
) -> ApplicationRead:
    try:
        next_state = ApplicationState(payload.stage.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unknown application stage") from exc

    async with async_session() as session:
        application = await session.get(Application, application_id)
        if not application or application.user_id != user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        previous_state = application.state
        application.state = next_state
        application.stage_number = APPLICATION_STAGE_ORDER[next_state]
        session.add(
            ApplicationStageTransition(
                application_id=application.id,
                user_id=user.id,
                from_state=previous_state,
                to_state=next_state,
                note=payload.note,
            )
        )
        await session.commit()
        await session.refresh(application)
        return application
