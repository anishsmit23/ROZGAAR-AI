"""Adzuna Jobs API scraper."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def fetch_jobs(
    role: str,
    location: str,
    remote: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Fetch jobs from Adzuna API.

    Args:
        role: Job title/role to search for
        location: Location to search in (e.g., 'Hyderabad', 'India')
        remote: Whether to filter for remote jobs
        limit: Maximum number of jobs to return

    Returns:
        List of job dictionaries with keys:
        title, company, location, description, source_url, salary_min, salary_max
    """
    settings = get_settings()

    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        logger.warning("Adzuna credentials not configured; returning empty list")
        return []

    # Adzuna uses country codes; default to IN for India
    country = "in"
    page = 1

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "results_per_page": min(limit, 50),  # Adzuna max is 50
                "what": role,
                "where": location,
                "full_time": "1" if not remote else "",
                "remote": "1" if remote else "",
            }
            # Remove empty values
            params = {k: v for k, v in params.items() if v}

            logger.info(f"Fetching jobs from Adzuna: role={role}, location={location}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for item in data.get("results", [])[:limit]:
                job_dict = {
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", "Unknown"),
                    "location": item.get("location", {}).get("display_name", location),
                    "description": item.get("description", ""),
                    "source_url": item.get("redirect_url", ""),
                    "salary_min": item.get("salary_min"),
                    "salary_max": item.get("salary_max"),
                }
                jobs.append(job_dict)

            logger.info(f"Fetched {len(jobs)} jobs from Adzuna")
            return jobs

    except httpx.HTTPError as e:
        logger.error(f"Adzuna API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching from Adzuna: {e}")
        return []
