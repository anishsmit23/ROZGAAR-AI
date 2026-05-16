from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.base import async_session
from app.db.models.application import Application
from app.db.models.job_posting import JobPosting
from app.db.models.user import User


def _target_role(user: User, jobs: list[JobPosting]) -> str:
    preferences = user.preferences or {}
    preferred_role = (
        preferences.get("target_role")
        or preferences.get("role")
        or preferences.get("query")
        or preferences.get("desired_role")
    )
    if preferred_role:
        return str(preferred_role)
    if jobs:
        return jobs[0].title
    return "Target role"


def _skills_summary(user: User) -> str:
    skills = user.skills or []
    if isinstance(skills, list) and skills:
        return ", ".join(str(skill) for skill in skills)
    if isinstance(skills, str):
        return skills
    return "No skills provided"


def _score_from_result(result: Any, metric_name: str) -> float | None:
    if isinstance(result, dict):
        value = result.get(metric_name)
        if isinstance(value, list):
            value = sum(value) / len(value) if value else None
        return float(value) if value is not None else None

    if hasattr(result, metric_name):
        value = getattr(result, metric_name)
        return float(value) if value is not None else None

    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        if metric_name in frame:
            series = frame[metric_name].dropna()
            return float(series.mean()) if len(series) else None

    return None


async def evaluate_ranking_quality(user_id: str, sample_size: int = 10) -> dict:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import context_precision, context_recall

    user_uuid = UUID(str(user_id))
    sample_size = max(1, sample_size)

    async with async_session() as session:
        user = await session.get(User, user_uuid)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        stmt = (
            select(Application, JobPosting)
            .join(JobPosting, Application.job_posting_id == JobPosting.id)
            .where(Application.user_id == user_uuid, Application.stage_number >= 2)
            .order_by(Application.created_at.desc())
            .limit(sample_size)
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        return {"context_precision": None, "context_recall": None, "sample_size": 0}

    jobs = [job for _, job in rows]
    question = f"Target role: {_target_role(user, jobs)}. Skills: {_skills_summary(user)}"

    dataset = Dataset.from_list(
        [
            {
                "question": question,
                "contexts": [job.description or ""],
                "answer": str(job.semantic_score if job.semantic_score is not None else 0.0),
                "ground_truth": "relevant" if (job.semantic_score or 0.0) >= 0.7 else "not_relevant",
            }
            for _, job in rows
        ]
    )

    result = await asyncio.to_thread(evaluate, dataset, metrics=[context_precision, context_recall])
    return {
        "context_precision": _score_from_result(result, "context_precision"),
        "context_recall": _score_from_result(result, "context_recall"),
        "sample_size": len(rows),
    }
