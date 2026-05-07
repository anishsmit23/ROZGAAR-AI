"""
Generate node - LLM call with prompt templates.
"""

import json
import logging
from typing import Any

from app.llm import get_llm_client
from app.llm.prompts import (
    TAILOR_RESUME_FOR_JOB,
    GENERATE_EMAIL_TO_RECRUITER,
    GENERATE_INTERVIEW_QUESTIONS,
    GENERATE_MODEL_ANSWERS,
    NORMALIZE_JOB_DESCRIPTION,
    EXTRACT_KEY_SKILLS,
)

logger = logging.getLogger(__name__)


def generate_with_llm(
    template: str,
    template_vars: dict[str, Any],
    temperature: float = 0.2,
    max_retries: int = 2,
) -> str:
    """
    Call LLM with a prompt template.
    
    Args:
        template: Prompt template string (with {variable} placeholders)
        template_vars: Dictionary of variables to inject
        temperature: LLM temperature (0-1)
        max_retries: Max retry attempts
        
    Returns:
        Generated text from LLM
    """
    llm_client = get_llm_client()
    
    # Format template with variables
    try:
        prompt = template.format(**template_vars)
    except KeyError as e:
        logger.error(f"Missing template variable: {e}")
        raise ValueError(f"Missing template variable: {e}")
    
    # Invoke LLM with retry fallback
    for attempt in range(max_retries):
        try:
            response = llm_client.invoke(
                prompt=prompt,
                temperature=temperature,
                streaming=False,
            )
            logger.info(f"LLM generation successful on attempt {attempt + 1}")
            return response
        except Exception as e:
            logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"LLM failed after {max_retries} attempts: {e}")
    
    return ""


def generate_structured(
    template: str,
    template_vars: dict[str, Any],
    output_schema: type,
    temperature: float = 0.2,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Call LLM with structured JSON output.
    
    Args:
        template: Prompt template string
        template_vars: Dictionary of variables to inject
        output_schema: Pydantic model for validation
        temperature: LLM temperature (0-1)
        max_retries: Max retry attempts
        
    Returns:
        Parsed JSON response
    """
    llm_client = get_llm_client()
    
    # Format template
    try:
        prompt = template.format(**template_vars)
    except KeyError as e:
        logger.error(f"Missing template variable: {e}")
        raise ValueError(f"Missing template variable: {e}")
    
    # Invoke with structured output
    for attempt in range(max_retries):
        try:
            response = llm_client.invoke_structured(
                prompt=prompt,
                output_schema=output_schema,
                temperature=temperature,
            )
            logger.info(f"Structured LLM generation successful on attempt {attempt + 1}")
            return response
        except Exception as e:
            logger.warning(f"Structured LLM attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Structured LLM failed after {max_retries} attempts: {e}")
    
    return {}


# ============================================================================
# SPECIALIZED GENERATORS
# ============================================================================

def generate_tailored_resume(
    job_description: str,
    original_resume: str,
    highlighted_sections: str,
) -> str:
    """Generate a resume tailored to a specific job."""
    return generate_with_llm(
        template=TAILOR_RESUME_FOR_JOB,
        template_vars={
            "job_description": job_description,
            "resume": original_resume,
            "highlighted_sections": highlighted_sections,
        },
        temperature=0.3,  # Lower temp for more focused output
    )


def generate_email_to_recruiter(
    job_description: str | None = None,
    resume_context: str | None = None,
    job_title: str | None = None,
    company: str | None = None,
    recruiter_name: str | None = None,
    candidate_name: str | None = None,
    key_skills: str | None = None,
    top_achievement: str | None = None,
) -> str:
    """Generate a professional email to a recruiter."""
    # Handle both call signatures for flexibility
    if job_description and resume_context:
        # Simple version for RAG-based email generation
        return generate_with_llm(
            template=GENERATE_EMAIL_TO_RECRUITER,
            template_vars={
                "job_title": job_title or "Target Position",
                "company": company or "Target Company",
                "recruiter_name": recruiter_name or "Hiring Manager",
                "candidate_name": candidate_name or "Candidate",
                "key_skills": key_skills or resume_context[:200],
                "top_achievement": top_achievement or "Strong track record",
            },
            temperature=0.5,
        )
    else:
        # Full version with all parameters
        return generate_with_llm(
            template=GENERATE_EMAIL_TO_RECRUITER,
            template_vars={
                "job_title": job_title or "Target Position",
                "company": company or "Target Company",
                "recruiter_name": recruiter_name or "Hiring Manager",
                "candidate_name": candidate_name or "Candidate",
                "key_skills": key_skills or "relevant skills",
                "top_achievement": top_achievement or "Strong background",
            },
            temperature=0.5,  # Slightly higher for natural tone
        )


def generate_interview_questions(
    job_title: str,
    company: str,
    job_description: str,
    candidate_background: str,
) -> str:
    """Generate likely interview questions for a role."""
    return generate_with_llm(
        template=GENERATE_INTERVIEW_QUESTIONS,
        template_vars={
            "job_title": job_title,
            "company": company,
            "job_description": job_description,
            "candidate_background": candidate_background,
        },
        temperature=0.3,
    )


def generate_model_answer(
    candidate_background: str,
    interview_question: str,
) -> str:
    """Generate a strong model answer to an interview question."""
    return generate_with_llm(
        template=GENERATE_MODEL_ANSWERS,
        template_vars={
            "candidate_background": candidate_background,
            "interview_question": interview_question,
        },
        temperature=0.2,
    )
