"""Normalize job description node."""

import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NormalizedJobDescription(BaseModel):
    job_title: str
    company: str
    location: str
    seniority_level: str
    employment_type: str
    key_skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    remote_type: str


def normalize_job_description(job_description: str) -> dict[str, Any]:
    from app.llm import get_llm_client
    from app.llm.prompts import NORMALIZE_JOB_DESCRIPTION
    llm_client = get_llm_client()
    prompt = NORMALIZE_JOB_DESCRIPTION.format(job_description=job_description)
    try:
        result = llm_client.invoke_structured(prompt=prompt, output_schema=NormalizedJobDescription, temperature=0.1)
        logger.info(f"Normalized job: {result.get('job_title')} at {result.get('company')}")
        return result
    except Exception as e:
        logger.error(f"Job normalization failed: {e}")
        return {"job_title": "Unknown", "company": "Unknown", "location": "Unknown", "error": str(e)}
