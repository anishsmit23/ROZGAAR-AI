"""Web search node - Search for jobs."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def search_jobs_web(query: str, location: str = "", max_results: int = 10) -> list[dict[str, Any]]:
    from google_search_results import GoogleSearch
    from app.config import get_settings
    
    settings = get_settings()
    search_query = f"{query} in {location}" if location else query
    try:
        params = {"q": search_query, "tbm": "lcm", "api_key": settings.serpapi_key, "num": max_results}
        search = GoogleSearch(params)
        results = search.get_dict()
        jobs = []
        for job in results.get("jobs_results", []):
            jobs.append({"title": job.get("title"), "company": job.get("company_name"), "location": job.get("location"), "link": job.get("link"), "description": job.get("description")})
        logger.info(f"Found {len(jobs)} jobs for: {search_query}")
        return jobs
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []
