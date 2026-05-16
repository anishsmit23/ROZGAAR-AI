from __future__ import annotations

import asyncio
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone

import redis
from celery import Task
from sqlalchemy import func, select

from app.agents.llm_client import call_groq
from app.agents.prompts import cold_email_prompt, resume_customization_prompt
from app.config import get_settings
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
from app.db.models.rag_evaluation import RagEvaluation
from app.db.models.user import User
from app.evaluation.ragas_eval import evaluate_ranking_quality
from app.scrapers import adzuna, remotive
from app.storage.minio_client import upload_pdf
from app.tasks.celery_app import celery_app
from app.vector.chroma_client import VectorStore
from app.utils.pdf_generator import markdown_to_pdf

logger = logging.getLogger(__name__)


class AgentTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 120

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            asyncio.run(_handle_task_failure(self.name, task_id, args, kwargs, exc, einfo))
            _publish_task_status(
                task_id=task_id,
                state="FAILURE",
                stage=ApplicationState.FAILED.value,
                application_id=_failure_context(self.name, args, kwargs)[1],
                error=str(exc),
            )
        except Exception:
            logger.error("Failed to persist Celery failure metadata for task %s", task_id, exc_info=True)
        super().on_failure(exc, task_id, args, kwargs, einfo)


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


def _publish_task_status(
    task_id: str | None,
    state: str,
    stage: str | None = None,
    application_id: str | None = None,
    error: str | None = None,
) -> None:
    if not task_id:
        logger.warning("Cannot publish task status without a task_id")
        return

    payload = {
        "state": state,
        "stage": stage,
        "application_id": application_id,
        "error": error,
    }
    try:
        settings = get_settings()
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            client.publish(f"task:{task_id}:status", json.dumps(payload))
        finally:
            client.close()
    except Exception:
        logger.error("Failed to publish task status for task %s", task_id, exc_info=True)


def _failure_context(task_name: str, args: tuple, kwargs: dict) -> tuple[str | None, str | None, str | None]:
    user_id = kwargs.get("user_id") if kwargs else None
    application_id = kwargs.get("application_id") if kwargs else None
    run_id = kwargs.get("run_id") if kwargs else None

    if args:
        user_id = user_id or args[0]
    if len(args) >= 3:
        run_id = run_id or args[2]
    if "run_resume_tailor" in task_name or "run_email_generation" in task_name:
        if len(args) >= 2:
            application_id = application_id or args[1]

    return (
        str(user_id) if user_id else None,
        str(application_id) if application_id else None,
        str(run_id) if run_id else None,
    )


async def _handle_task_failure(task_name: str, task_id: str, args: tuple, kwargs: dict, exc: BaseException, einfo) -> None:
    user_id, application_id, run_id = _failure_context(task_name, args, kwargs)
    error = str(exc)
    traceback_text = getattr(einfo, "traceback", None) or "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )

    if run_id:
        await _set_run_status(
            run_id,
            "failed",
            output={
                "task_id": task_id,
                "application_id": application_id,
                "stage": ApplicationState.FAILED.value if application_id else None,
                "error": error,
                "traceback": traceback_text,
            },
            error=error,
        )

    if run_id and user_id:
        await _log_event(
            run_id,
            user_id,
            "task_failed",
            {
                "task_name": task_name,
                "task_id": task_id,
                "application_id": application_id,
                "error": error,
                "traceback": traceback_text,
            },
        )

    if application_id and user_id:
        await _set_application_state(
            application_id,
            user_id,
            ApplicationState.FAILED,
            f"Task failed after retries: {error}",
        )


@celery_app.task(
    bind=True,
    base=AgentTask,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="agents",
)
def run_job_search(self, user_id: str, query_params: dict, run_id: str) -> dict:
    """
    Execute job search pipeline with semantic ranking.
    
    Args:
        user_id: UUID of the user
        query_params: Search parameters (query, location, remote, limit)
        run_id: UUID of the agent run
    
    Returns:
        Dictionary with job search results and counts
    """
    async def _run() -> dict:
        try:
            await _set_run_status(run_id, "running")
            await _log_event(run_id, user_id, "search_started", {"query": query_params})

            # Extract search parameters
            role = query_params.get("query", "")
            location = query_params.get("location", "")
            remote = query_params.get("remote", False)
            limit = query_params.get("limit", 25)

            # Fetch jobs from scrapers (Adzuna first, fallback to Remotive)
            jobs = await adzuna.fetch_jobs(role, location, remote, limit)
            
            if not jobs:
                logger.info(f"No jobs from Adzuna, falling back to Remotive for role={role}")
                jobs = await remotive.fetch_jobs(role, limit)

            if not jobs:
                logger.warning(f"No jobs found for role={role}, location={location}")
                await _log_event(run_id, user_id, "search_completed", {"total": 0, "note": "no jobs found"})
                output = {
                    "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                    "jobs_discovered": 0,
                }
                await _set_run_status(run_id, "completed", output)
                return output

            # Rank jobs using semantic similarity to user's resume
            logger.info(f"Ranking {len(jobs)} jobs for user {user_id}")
            vector_store = VectorStore()
            # Run ranking in thread pool since ChromaDB is synchronous
            jobs = await asyncio.to_thread(vector_store.rank_jobs, user_id, jobs)
            
            # Filter jobs by semantic score threshold
            ranked_jobs = [j for j in jobs if j.get("semantic_score", 0.0) >= 0.5]
            logger.info(f"After filtering by score >= 0.5: {len(ranked_jobs)} qualified jobs out of {len(jobs)}")

            if not ranked_jobs:
                logger.warning(f"No jobs met relevance threshold for user {user_id}")
                await _log_event(run_id, user_id, "search_completed", {"total": 0, "note": "no jobs above threshold"})
                output = {
                    "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                    "jobs_discovered": 0,
                }
                await _set_run_status(run_id, "completed", output)
                return output

            # Create JobPosting and Application records for each ranked job
            created_count = 0
            user_uuid = uuid.UUID(user_id)
            run_uuid = uuid.UUID(run_id)

            async with async_session() as session:
                for job_data in ranked_jobs:
                    try:
                        # Create JobPosting with semantic score
                        semantic_score = job_data.get("semantic_score", 0.0)
                        job_posting = JobPosting(
                            user_id=user_uuid,
                            title=job_data.get("title", ""),
                            company=job_data.get("company", "Unknown"),
                            location=job_data.get("location", location),
                            description=job_data.get("description", ""),
                            source="adzuna" if "adzuna" in job_data.get("source_url", "") else "remotive",
                            source_url=job_data.get("source_url", ""),
                            semantic_score=semantic_score,
                        )
                        session.add(job_posting)
                        await session.flush()
                        await session.refresh(job_posting)

                        # Create Application linked to this job
                        application = Application(
                            user_id=user_uuid,
                            job_posting_id=job_posting.id,
                            state=ApplicationState.DISCOVERED,
                            stage_number=APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED],
                        )
                        session.add(application)
                        await session.flush()
                        await session.refresh(application)

                        # Record stage transition
                        session.add(
                            ApplicationStageTransition(
                                application_id=application.id,
                                user_id=user_uuid,
                                from_state=None,
                                to_state=ApplicationState.DISCOVERED,
                                note=f"Job discovered: {job_posting.title} at {job_posting.company} (score: {semantic_score:.3f})",
                            )
                        )

                        # Log event for this job
                        await _log_event(
                            run_id,
                            user_id,
                            "job_discovered",
                            {
                                "job_id": str(job_posting.id),
                                "title": job_posting.title,
                                "company": job_posting.company,
                                "semantic_score": semantic_score,
                            },
                        )

                        created_count += 1
                        logger.info(f"Created job posting: {job_posting.title} at {job_posting.company} (score: {semantic_score:.3f})")

                    except Exception as e:
                        logger.error(f"Error creating job posting for {job_data.get('title')}: {e}", exc_info=True)
                        continue

                await session.commit()

            await _log_event(run_id, user_id, "search_completed", {"total": created_count})
            output = {
                "completed_at": datetime.now(tz=timezone.utc).isoformat(),
                "jobs_discovered": created_count,
            }
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Job search completed: discovered {created_count} jobs for user {user_id}")
            return output

        except Exception as e:
            logger.error(f"Error in job search for user {user_id}: {e}", exc_info=True)
            raise

    result = asyncio.run(_run())
    _publish_task_status(
        task_id=self.request.id,
        state="SUCCESS",
        stage=ApplicationState.DISCOVERED.value,
        application_id=result.get("application_id") if isinstance(result, dict) else None,
    )
    return result


@celery_app.task(
    bind=True,
    base=AgentTask,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="agents",
)
def run_resume_tailor(self, user_id: str, application_id: str, run_id: str) -> dict:
    """
    Execute resume tailoring pipeline with LLM-powered customization.
    
    Args:
        user_id: UUID of the user
        application_id: UUID of the application
        run_id: UUID of the agent run
    
    Returns:
        Dictionary with tailored resume information and MinIO path
    """
    async def _run() -> dict:
        try:
            await _set_run_status(run_id, "running")
            await _log_event(run_id, user_id, "tailor_started", {"application_id": application_id})

            application_uuid = uuid.UUID(application_id)
            user_uuid = uuid.UUID(user_id)

            # Load application, job posting, and user from database
            async with async_session() as session:
                application = await session.get(Application, application_uuid)
                if not application:
                    raise ValueError(f"Application not found: {application_id}")

                job_posting = await session.get(JobPosting, application.job_posting_id)
                if not job_posting:
                    raise ValueError(f"Job posting not found for application: {application_id}")

                user = await session.get(User, user_uuid)
                if not user:
                    raise ValueError(f"User not found: {user_id}")

                if not user.resume_text:
                    raise ValueError(f"User has no resume: {user_id}")

                applicant_name = user.full_name or "Candidate"

            logger.info(f"Loaded data for tailoring: app={application_id}, job={job_posting.title}")

            # Generate customization prompt
            await _log_event(run_id, user_id, "generating_prompt", {"job_title": job_posting.title})
            system_prompt, user_prompt = resume_customization_prompt(
                user.resume_text,
                job_posting.title,
                job_posting.company,
                job_posting.description,
            )

            # Call Groq LLM to customize resume
            await _log_event(run_id, user_id, "calling_llm", {})
            logger.info(f"Calling Groq to customize resume for {job_posting.title} at {job_posting.company}")
            
            customized_resume_md = await call_groq(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=2000,
            )

            logger.info(f"Received customized resume ({len(customized_resume_md)} chars)")
            await _log_event(run_id, user_id, "llm_completed", {"resume_length": len(customized_resume_md)})

            # Convert Markdown to PDF
            await _log_event(run_id, user_id, "converting_to_pdf", {})
            logger.info("Converting customized resume to PDF")
            
            pdf_bytes = await asyncio.to_thread(markdown_to_pdf, customized_resume_md, applicant_name)
            logger.info(f"Generated PDF ({len(pdf_bytes)} bytes)")

            # Upload to MinIO
            await _log_event(run_id, user_id, "uploading_to_minio", {})
            
            # Generate MinIO key with version
            version = 1
            minio_key = f"{application_id}/resume_v{version}.pdf"
            
            await upload_pdf(minio_key, pdf_bytes)
            
            logger.info(f"Uploaded resume to MinIO: {minio_key}")
            await _log_event(run_id, user_id, "minio_uploaded", {"minio_key": minio_key})

            # Update application with resume path
            async with async_session() as session:
                application = await session.get(Application, application_uuid)
                application.resume_version_path = minio_key
                await session.commit()
                logger.info(f"Updated application resume_version_path: {minio_key}")

            # Transition application state to RESUME_CUSTOMIZED
            await _log_event(run_id, user_id, "updating_state", {"to_state": ApplicationState.RESUME_CUSTOMIZED})
            await _set_application_state(
                application_id,
                user_id,
                ApplicationState.RESUME_CUSTOMIZED,
                f"Resume customized and uploaded to MinIO: {minio_key}",
            )

            output = {
                "application_id": application_id,
                "minio_key": minio_key,
                "resume_length": len(customized_resume_md),
                "pdf_size": len(pdf_bytes),
                "status": "completed",
            }
            await _log_event(run_id, user_id, "tailor_completed", output)
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Resume tailoring completed: {output}")
            return output

        except Exception as e:
            logger.error(f"Error in resume tailoring for application {application_id}: {e}", exc_info=True)
            await _log_event(run_id, user_id, "tailor_failed", {"error": str(e)})
            raise

    result = asyncio.run(_run())
    _publish_task_status(
        task_id=self.request.id,
        state="SUCCESS",
        stage=ApplicationState.RESUME_CUSTOMIZED.value,
        application_id=result.get("application_id") if isinstance(result, dict) else application_id,
    )
    return result


@celery_app.task(
    bind=True,
    base=AgentTask,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="agents",
)
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
            
            application_uuid = uuid.UUID(application_id)
            user_uuid = uuid.UUID(user_id)

            async with async_session() as session:
                application = await session.get(Application, application_uuid)
                if not application:
                    raise ValueError(f"Application not found: {application_id}")

                job_posting = await session.get(JobPosting, application.job_posting_id)
                if not job_posting:
                    raise ValueError(f"Job posting not found for application: {application_id}")

                user = await session.get(User, user_uuid)
                if not user:
                    raise ValueError(f"User not found: {user_id}")

                user_skills = user.skills or []
                experience_years = user.experience_years or 0
                user_name = user.full_name or "Candidate"

                prompt = cold_email_prompt(
                    user_name=user_name,
                    user_skills=user_skills,
                    experience_years=experience_years,
                    job_title=job_posting.title,
                    company=job_posting.company,
                    job_description=job_posting.description,
                )

            await _log_event(run_id, user_id, "email_prompt_created", {"job_title": job_posting.title, "company": job_posting.company})

            cold_email = await call_groq(
                prompt=prompt,
                system="You write concise, tailored cold outreach emails for job applications.",
                max_tokens=900,
            )

            async with async_session() as session:
                application = await session.get(Application, application_uuid)
                if not application:
                    raise ValueError(f"Application not found: {application_id}")
                application.email_draft = cold_email
                await session.commit()

            await _log_event(run_id, user_id, "email_completed", {"application_id": application_id, "email_length": len(cold_email)})
            await _set_application_state(
                application_id,
                user_id,
                ApplicationState.EMAIL_GENERATED,
                "Cold email generated by LLM",
            )

            output = {
                "application_id": application_id,
                "status": "completed",
                "email_length": len(cold_email),
            }
            await _set_run_status(run_id, "completed", output)
            logger.info(f"Email generation completed for application {application_id}")
            return output
        except Exception as e:
            logger.error(f"Error in email generation for application {application_id}: {e}", exc_info=True)
            raise

    result = asyncio.run(_run())
    _publish_task_status(
        task_id=self.request.id,
        state="SUCCESS",
        stage=ApplicationState.EMAIL_GENERATED.value,
        application_id=result.get("application_id") if isinstance(result, dict) else application_id,
    )
    return result


@celery_app.task(name="app.tasks.agent_tasks.run_rag_evaluation", queue="agents")
def run_rag_evaluation(sample_size: int = 10) -> dict:
    async def _run() -> dict:
        evaluated = 0
        skipped = 0
        errors: list[dict[str, str]] = []

        async with async_session() as session:
            stmt = (
                select(User.id, func.count(Application.id).label("ranked_count"))
                .join(Application, Application.user_id == User.id)
                .where(Application.stage_number >= APPLICATION_STAGE_ORDER[ApplicationState.RANKED])
                .group_by(User.id)
                .having(func.count(Application.id) >= 5)
            )
            result = await session.execute(stmt)
            user_ids = [str(row.id) for row in result]

        for user_id in user_ids:
            try:
                scores = await evaluate_ranking_quality(user_id, sample_size=sample_size)
                actual_sample_size = int(scores.get("sample_size") or 0)
                if actual_sample_size < 1:
                    skipped += 1
                    continue

                async with async_session() as session:
                    session.add(
                        RagEvaluation(
                            user_id=uuid.UUID(user_id),
                            context_precision=scores.get("context_precision"),
                            context_recall=scores.get("context_recall"),
                            sample_size=actual_sample_size,
                        )
                    )
                    await session.commit()
                evaluated += 1
            except Exception as exc:
                logger.error("RAG evaluation failed for user %s: %s", user_id, exc, exc_info=True)
                errors.append({"user_id": user_id, "error": str(exc)})

        return {"evaluated": evaluated, "skipped": skipped, "errors": errors}

    return asyncio.run(_run())
