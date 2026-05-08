from __future__ import annotations

import asyncio
import logging

from app.scrapers.serpapi import SerpApiScraper
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, queue="scrapers")
def scrape_job_board(self, source: str, query: dict) -> dict:
    """Scrape job listings from specified source.
    
    Args:
        source: Job board source ("serpapi", "indeed", "linkedin", "naukri")
        query: Search query dict with 'q' and 'location'
        
    Returns:
        Result dict with scraped jobs or error info
    """
    try:
        if source.lower() == "serpapi":
            scraper = SerpApiScraper()
            jobs = asyncio.run(scraper.search(query))
            return {
                "source": source,
                "status": "success",
                "jobs_count": len(jobs),
                "jobs": jobs,
            }
        else:
            logger.warning(f"Unsupported source: {source}")
            return {
                "source": source,
                "status": "error",
                "message": f"Unsupported scraper source: {source}",
            }
    except Exception as e:
        logger.error(f"Scraping failed for {source}: {e}")
        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        return {
            "source": source,
            "status": "error",
            "message": str(e),
            "retries_exceeded": True,
        }
