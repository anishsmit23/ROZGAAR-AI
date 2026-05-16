from __future__ import annotations

from inspect import isawaitable
import logging

import httpx

from app.config import get_settings
from app.scrapers.base import BaseJobScraper

logger = logging.getLogger(__name__)


class SerpAPIJobScraper:
    """SerpAPI Google Jobs scraper with async support."""
    
    BASE_URL = "https://serpapi.com/search"
    TIMEOUT = 30
    MAX_RETRIES = 3

    async def search_jobs(self, query: str, location: str = "India") -> list[dict]:
        """Search for jobs using SerpAPI Google Jobs engine.
        
        Args:
            query: Job search query (e.g., "Python Developer")
            location: Job location (default: "India")
            
        Returns:
            List of normalized job dictionaries
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []
        
        settings = get_settings()
        if not settings.serpapi_key:
            logger.error("SERPAPI_KEY not configured")
            return []
        
        params = {
            "engine": "google_jobs",
            "q": query.strip(),
            "location": location,
            "api_key": settings.serpapi_key,
            "hl": "en",
            "num": 20,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                if isawaitable(data):
                    data = await data
                jobs = data.get("jobs_results", [])
                logger.info(f"Found {len(jobs)} jobs for '{query}' in {location}")
                return jobs
        except httpx.HTTPStatusError as e:
            logger.error(f"SerpAPI HTTP error {e.response.status_code}: {e}")
            return []
        except httpx.TimeoutException:
            logger.error(f"SerpAPI request timed out for query: {query}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI scrape failed for '{query}': {e}")
            return []

    def normalize(self, raw_job: dict) -> dict:
        """Normalize raw SerpAPI job result to standard format.
        
        Args:
            raw_job: Raw job data from SerpAPI
            
        Returns:
            Normalized job dictionary
        """
        return {
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company_name", ""),
            "location": raw_job.get("location", ""),
            "description": raw_job.get("description", ""),
            "source_url": raw_job.get("link", ""),
            "posted_at": raw_job.get("detected_extensions", {}).get("posted_at", ""),
            "source": "serpapi",
        }


class SerpApiScraper(BaseJobScraper):
    """BaseJobScraper implementation for SerpAPI."""
    
    def __init__(self):
        self.scraper = SerpAPIJobScraper()
    
    async def search(self, query: dict) -> list[dict]:
        """Search for jobs and return normalized results.
        
        Args:
            query: Search parameters with keys:
                - query/q: Search query string
                - location: Job location (optional, default: "India")
                
        Returns:
            List of normalized job dictionaries
        """
        search_query = query.get("query") or query.get("q") or ""
        location = query.get("location", "India")
        
        if not search_query:
            logger.warning("No search query provided")
            return []
        
        raw_jobs = await self.scraper.search_jobs(search_query, location=location)
        normalized_jobs = [self.scraper.normalize(job) for job in raw_jobs]
        return normalized_jobs
