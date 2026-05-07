"""Scorer node - Evaluate outputs with JSON schema validation."""

import logging
from typing import Any
from pydantic import BaseModel, Field

from app.llm import get_llm_client
from app.llm.prompts import EVALUATE_TAILORED_RESUME, EVALUATE_EMAIL

logger = logging.getLogger(__name__)


class ResumeScorerOutput(BaseModel):
    keyword_match: int = Field(ge=1, le=10)
    skills_alignment: int = Field(ge=1, le=10)
    achievement_fit: int = Field(ge=1, le=10)
    readability: int = Field(ge=1, le=10)
    overall_score: float = Field(ge=1, le=10)
    strengths: list[str]
    improvements: list[str]
    recommendation: str


class EmailScorerOutput(BaseModel):
    professionalism: int = Field(ge=1, le=10)
    relevance: int = Field(ge=1, le=10)
    personalization: int = Field(ge=1, le=10)
    clarity: int = Field(ge=1, le=10)
    overall_score: float = Field(ge=1, le=10)
    strengths: list[str]
    improvements: list[str]
    recommendation: str


def score_output(output_type: str, output_content: str, context: dict[str, Any], score_threshold: int = 7) -> dict[str, Any]:
    if output_type == "resume":
        return _score_resume(output_content, context, score_threshold)
    elif output_type == "email":
        return _score_email(output_content, context, score_threshold)
    else:
        logger.warning(f"Unknown output type: {output_type}")
        return {"overall_score": 0, "recommendation": "unknown"}


def _score_resume(tailored_resume: str, context: dict[str, Any], score_threshold: int) -> dict[str, Any]:
    llm_client = get_llm_client()
    prompt = EVALUATE_TAILORED_RESUME.format(job_description=context.get("job_description", ""), tailored_resume=tailored_resume)
    try:
        result = llm_client.invoke_structured(prompt=prompt, output_schema=ResumeScorerOutput, temperature=0.1)
        logger.info(f"Resume scored: {result['overall_score']:.1f}/10")
        result["recommendation"] = "approve" if result["overall_score"] >= score_threshold else "retry"
        return result
    except Exception as e:
        logger.error(f"Resume scoring failed: {e}")
        return {"overall_score": 0, "recommendation": "error", "error": str(e)}


def _score_email(email_content: str, context: dict[str, Any], score_threshold: int) -> dict[str, Any]:
    """Score generated email against job description."""
    llm_client = get_llm_client()
    prompt = EVALUATE_EMAIL.format(job_description=context.get("job_description", ""), email=email_content)
    try:
        result = llm_client.invoke_structured(prompt=prompt, output_schema=EmailScorerOutput, temperature=0.1)
        logger.info(f"Email scored: {result['overall_score']:.1f}/10")
        result["recommendation"] = "approve" if result["overall_score"] >= score_threshold else "retry"
        return result
    except Exception as e:
        logger.error(f"Email scoring failed: {e}")
        return {"overall_score": 0, "recommendation": "error", "error": str(e)}
