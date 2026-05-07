from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.scrapers.serpapi import SerpAPIJobScraper


@pytest.mark.asyncio
async def test_serpapi_normalize():
    scraper = SerpAPIJobScraper()
    raw = {
        "title": "ML Engineer",
        "company_name": "Sarvam AI",
        "location": "Bangalore",
        "description": "Build LLMs",
        "related_links": [{"link": "https://example.com"}],
    }
    result = scraper.normalize(raw)
    assert result["title"] == "ML Engineer"
    assert result["company"] == "Sarvam AI"


@pytest.mark.asyncio
async def test_serpapi_search_returns_list():
    scraper = SerpAPIJobScraper()
    mock_response = {"jobs_results": [{"title": "AI Intern", "company_name": "Test Co"}]}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        results = await scraper.search_jobs("AI engineer India")
        assert isinstance(results, list)
