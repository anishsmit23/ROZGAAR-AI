from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.db.base import async_session
from app.db.models.agent_event import AgentEvent
from app.db.models.agent_run import AgentRun
from app.db.models.application import (
    APPLICATION_STAGE_ORDER,
    Application,
    ApplicationStageTransition,
    ApplicationState,
)
from app.db.models.job_posting import JobPosting
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _set_run_status(run_id: str, status: str, output: dict | None = None, error: str | None = None) -> None:
    """Update agent run status in database."""
    try:
        async with async_session() as session:
            run = await session.get(AgentRun, uuid.UUID(run_id))
            if not run:
                logger.warning(f"AgentRun not found: {run_id}")
                return
            run.status = status
            if output:
                run.output_snapshot = output
            if error:
                run.output_snapshot = run.output_snapshot or {}
                run.output_snapshot["error"] = error
            await session.commit()
            logger.info(f"Updated run {run_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update run status: {e}", exc_info=True)


async def _log_event(run_id: str, user_id: str, step_name: str, payload: dict | None = None) -> None:
    """Log agent event."""
    try:
        async with async_session() as session:
            event = AgentEvent(
                run_id=uuid.UUID(run_id),
                user_id=uuid.UUID(user_id),
                step_name=step_name,
                payload=payload or {},
            )
            session.add(event)
            await session.commit()
            logger.debug(f"Logged event: {step_name} for run {run_id}")
    except Exception as e:
        logger.error(f"Failed to log event: {e}", exc_info=True)


async def _set_application_state(application_id: str, user_id: str, state: ApplicationState, note: str | None = None) -> None:
    """Update application state and transition."""
    try:
        async with async_session() as session:
            application = await session.get(Application, uuid.UUID(application_id))
            if not application:
                logger.warning(f"Application not found: {application_id}")
                return
            previous_state = application.state
            application.state = state
            application.stage_number = APPLICATION_STAGE_ORDER[state]
            session.add(
                ApplicationStageTransition(
                    application_id=application.id,
                    user_id=uuid.UUID(user_id),
                    from_state=previous_state,
                    to_state=state,
                    note=note,
                )
            )
            await session.commit()
            logger.info(f"Updated application {application_id} state from {previous_state} to {state}")
    except Exception as e:
        logger.error(f"Failed to set application state: {e}", exc_info=True)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, queue="agents")
def run_job_search(self, user_id: str, query_params: dict, run_id: str) -> dict:
    """
    Execute job search pipeline with error handling and retry logic.
    
    Args:
        user_id: UUID of the user
        query_params: Search parameters (query, location, etc.)
        run_id: UUID of the agent run
    
    Returns:
        Dictionary with job search results
    """
    async def _run() -> dict:
        try:
            await _set_run_status(run_id, "running")
            await _log_event(run_id, user_id, "search_started", {"query": query_params})

            async with async_session() as session:
                job = JobPosting(
                    user_id=uuid.UUID(user_id),
                    title=query_params.get("query", "Target role"),
                    company="Sample Company",
                    location=query_params.get("location"),
                    description="Placeholder listing created by the v1 pipeline stub.",
                    source="pipeline",
                    source_url=None,
                    semantic_score=0.70,
                )
                session.add(job)
                await session.commit()
                await session.refresh(job)

                application = Application(
                    user_id=uuid.UUID(user_id),
                    job_posting_id=job.id,
                    state=ApplicationState.DISCOVERED,
                    stage_number=APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED],
                )
                session.add(application)
                await session.commit()
                await session.refresh(application)
                session.add(
                    ApplicationStageTransition(
                        application_id=application.id,
                        user_id=uuid.UUID(user_id),
                        from_state=None,
                        to_state=ApplicationState.DISCOVERED,
                        note="Pipeline discovered listing",
                    )
                )
                await session.commit()

            await _log_event(run_id, user_id, "search_completed", {"total": 1})
            output = {
                "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                "jobs_discovered": 1,
            }
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Job search completed for user {user_id}")
            return output
        except Exception as e:
            logger.error(f"Error in job search for user {user_id}: {e}", exc_info=True)
            await _set_run_status(run_id, "failed", error=str(e))
            raise

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Task run_job_search failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, queue="agents")
def run_resume_tailor(self, user_id: str, application_id: str, run_id: str) -> dict:
    """
    Execute resume tailoring pipeline with error handling and retry logic.
    
    Args:
        user_id: UUID of the user
        application_id: UUID of the application
        run_id: UUID of the agent run
    
    Returns:
        Dictionary with tailored resume information
    """
    async def _run() -> dict:
        try:
            await _set_run_status(run_id, "running")
            await _log_event(run_id, user_id, "tailor_started", {"application_id": application_id})
            
            async with async_session() as session:
                application = await session.get(Application, uuid.UUID(application_id))
                if not application:
                    raise ValueError(f"Application not found: {application_id}")
                
                # Simulate resume tailoring
                application.resume_version_path = f"minio://generated-resumes/{application_id}.pdf"
                await session.commit()
            
            await _log_event(run_id, user_id, "tailor_completed", {"application_id": application_id})
            await _set_application_state(
                application_id,
                user_id,
                ApplicationState.RESUME_CUSTOMIZED,
                "Resume draft generated",
            )
            
            output = {"application_id": application_id, "status": "completed"}
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Resume tailoring completed for application {application_id}")
            return output
        except Exception as e:
            logger.error(f"Error in resume tailoring for application {application_id}: {e}", exc_info=True)
            await _set_run_status(run_id, "failed", error=str(e))
            raise

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Task run_resume_tailor failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, queue="agents")
def run_email_generation(self, user_id: str, application_id: str, run_id: str) -> dict:
    """
    Execute email generation pipeline with error handling and retry logic.
    
    Args:
        user_id: UUID of the user
        application_id: UUID of the application
        run_id: UUID of the agent run
    
    Returns:
        Dictionary with generated email information
    """
    async def _run() -> dict:
        try:
            await _set_run_status(run_id, "running")
            await _log_event(run_id, user_id, "email_started", {"application_id": application_id})
            
            async with async_session() as session:
                application = await session.get(Application, uuid.UUID(application_id))
                if not application:
                    raise ValueError(f"Application not found: {application_id}")
                
                # Simulate email generation
                application.email_draft = "Hi, I am interested in this role and would love to discuss my fit."
                await session.commit()
            
            await _log_event(run_id, user_id, "email_completed", {"application_id": application_id})
            await _set_application_state(
                application_id,
                user_id,
                ApplicationState.EMAIL_GENERATED,
                "Cold email draft generated",
            )
            
            output = {"application_id": application_id, "status": "completed"}
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Email generation completed for application {application_id}")
            return output
        except Exception as e:
            logger.error(f"Error in email generation for application {application_id}: {e}", exc_info=True)
            await _set_run_status(run_id, "failed", error=str(e))
            raise

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"Task run_email_generation failed (attempt {self.request.retries}/{self.max_retries}): {e}")
        raise self.retry(exc=e, countdown=60)
