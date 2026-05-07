from __future__ import annotations

import inspect

import httpx

from app.config import settings
from app.scrapers.base import BaseJobScraper


class SerpAPIJobScraper:
    BASE_URL = "https://serpapi.com/search"

    async def search_jobs(self, query: str, location: str = "India") -> list[dict]:
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": settings.SERPAPI_KEY,
            "hl": "en",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if inspect.isawaitable(data):
                data = await data
            return data.get("jobs_results", [])

    def normalize(self, raw_job: dict) -> dict:
        related_links = raw_job.get("related_links") or [{}]
        return {
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company_name", ""),
            "location": raw_job.get("location", ""),
            "description": raw_job.get("description", ""),
            "source_url": related_links[0].get("link", ""),
            "posted_at": raw_job.get("detected_extensions", {}).get("posted_at", ""),
        }


class SerpApiScraper(BaseJobScraper):
    async def search(self, query: dict) -> list[dict]:
        scraper = SerpAPIJobScraper()
        search_query = query.get("query") or query.get("q") or ""
        location = query.get("location", "India")
        return await scraper.search_jobs(search_query, location=location)
