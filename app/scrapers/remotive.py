"""Remotive Jobs API scraper (fallback source)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def fetch_jobs(
    role: str,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Fetch remote jobs from Remotive API (fallback source).

    Args:
        role: Job title/role to search for
        limit: Maximum number of jobs to return

    Returns:
        List of job dictionaries with keys:
        title, company, location, description, source_url, salary_min, salary_max
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://remotive.com/api/remote-jobs"
            params = {
                "search": role,
                "limit": min(limit, 100),  # Remotive max is 100
            }

            logger.info(f"Fetching remote jobs from Remotive: role={role}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for item in data.get("jobs", [])[:limit]:
                # Remotive response structure
                job_dict = {
                    "title": item.get("title", ""),
                    "company": item.get("company_name", "Unknown"),
                    "location": item.get("job_apply_url", ""),  # Remotive doesn't always have explicit location
                    "description": item.get("description", ""),
                    "source_url": item.get("url", ""),
                    "salary_min": None,  # Remotive doesn't always provide salary
                    "salary_max": None,
                }
                jobs.append(job_dict)

            logger.info(f"Fetched {len(jobs)} jobs from Remotive")
            return jobs

    except httpx.HTTPError as e:
        logger.error(f"Remotive API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching from Remotive: {e}")
        return []
