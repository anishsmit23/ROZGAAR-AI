# ROZGAAR AI — Exact Next Steps to Make It Work
**Current State:** 15 tests passing | 48% coverage | Scrapers at 0%  
**Goal:** Fully working agent with live deployment  
**Estimated Time:** 2–3 weeks if you work daily

---

## PHASE 1 — Make Job Discovery Actually Work
> ⏱️ Est. Time: 3–4 days  
> 🎯 Goal: Agent can find real jobs and store them

### Step 1.1 — Get SerpAPI Key (Day 1)
SerpAPI is the easiest way to get real job listings without getting blocked by LinkedIn/Indeed.

1. Go to **https://serpapi.com** → Sign up (free tier = 100 searches/month)
2. Go to Dashboard → copy your **API Key**
3. Add to your `.env`:
```dotenv
SERPAPI_KEY=your_key_here
```

### Step 1.2 — Implement `scrapers/serpapi.py` (Day 1–2)
Your file currently has 0% coverage because it's a stub. Replace it with this:

```python
# app/scrapers/serpapi.py
import httpx
from app.config import settings

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
            return data.get("jobs_results", [])

    def normalize(self, raw_job: dict) -> dict:
        return {
            "title": raw_job.get("title", ""),
            "company": raw_job.get("company_name", ""),
            "location": raw_job.get("location", ""),
            "description": raw_job.get("description", ""),
            "source_url": raw_job.get("related_links", [{}])[0].get("link", ""),
            "posted_at": raw_job.get("detected_extensions", {}).get("posted_at", ""),
        }
```

### Step 1.3 — Add `SERPAPI_KEY` to `config.py` (Day 2)
Open `app/config.py` and add:
```python
SERPAPI_KEY: str = ""
```

### Step 1.4 — Write Scraper Test (Day 2)
Create `tests/test_scrapers.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
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
```

Run: `pytest tests/test_scrapers.py -v`

---

## PHASE 2 — Fix Redis & MinIO Connections
> ⏱️ Est. Time: 1–2 days  
> 🎯 Goal: Cache and storage actually connect

### Step 2.1 — Implement `cache/redis.py`
Currently 0%. Open `app/cache/redis.py` and make sure it looks like:

```python
# app/cache/redis.py
import redis.asyncio as aioredis
from app.config import settings

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client

async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
```

### Step 2.2 — Implement `storage/minio.py`
Currently 0%. Update it:

```python
# app/storage/minio.py
from minio import Minio
from app.config import settings
import io

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False
)

def ensure_bucket():
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)

def upload_file(filename: str, data: bytes, content_type: str = "application/pdf"):
    ensure_bucket()
    client.put_object(
        settings.MINIO_BUCKET,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type
    )

def download_file(filename: str) -> bytes:
    response = client.get_object(settings.MINIO_BUCKET, filename)
    return response.read()
```

### Step 2.3 — Write Connection Tests
Create `tests/test_connections.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_redis_set_get():
    with patch("redis.asyncio.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = "rozgaar"
        mock_redis.return_value = mock_client
        from app.cache.redis import get_redis
        r = await get_redis()
        val = await r.get("test")
        assert val == "rozgaar"

def test_minio_ensure_bucket():
    with patch("minio.Minio.bucket_exists", return_value=False), \
         patch("minio.Minio.make_bucket") as mock_make:
        from app.storage.minio import ensure_bucket
        ensure_bucket()
        mock_make.assert_called_once()
```

---

## PHASE 3 — Fix the Agent Pipeline Core
> ⏱️ Est. Time: 4–5 days  
> 🎯 Goal: Full pipeline runs end to end

### Step 3.1 — Check `tasks/agent_tasks.py` (15% coverage — most critical)

Open the file and find every function that has no test. For each one, you need to either:
- Write a unit test with mocked LLM calls, OR
- Verify it actually runs when you call it manually

Run this to see exactly which lines are missing:
```bash
pytest --cov=app/tasks/agent_tasks.py --cov-report=term-missing
```
Look at the `Miss` column — those line numbers are your untested code.

### Step 3.2 — Mock LLM Calls in Tests
The reason `llm/client.py` is at 17% is that real LLM calls are expensive to test. Use mocks:

```python
# In any test file that uses LLM
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_resume_tailor_node():
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Tailored resume content here"
    
    with patch("app.llm.client.get_llm") as mock_llm:
        mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_llm_response)
        # now call your node function
        from app.agents.nodes.generate import generate_resume
        result = await generate_resume({"job_description": "AI Engineer", "resume": "..."})
        assert result is not None
```

### Step 3.3 — Test the 8-Stage Application Tracker
This is what makes your project unique — make sure it actually works:

```python
# tests/test_application_stages.py
import pytest
from app.db.models.application import ApplicationStage

def test_all_8_stages_exist():
    stages = [s.value for s in ApplicationStage]
    assert len(stages) == 8

def test_stage_progression_order():
    # stages should go 1 → 8, not jump
    stage_values = [s.value for s in ApplicationStage]
    assert stage_values == sorted(stage_values)
```

---

## PHASE 4 — Get It Running with Docker
> ⏱️ Est. Time: 1–2 days  
> 🎯 Goal: `docker compose up` works completely

### Step 4.1 — Start Docker Desktop
Make sure Docker Desktop is running on your Windows machine.

### Step 4.2 — Build and Start All Services
```bash
cd C:\projects\ROZGAAR-AGENT
docker compose up --build
```

Watch for these in the logs — all must appear:
```
✅ postgres     | database system is ready to accept connections
✅ redis        | Ready to accept connections
✅ chroma       | Application startup complete
✅ minio        | API: http://0.0.0.0:9000
✅ api          | Application startup complete
✅ worker       | celery@... ready
✅ streamlit    | You can now view your Streamlit app
```

### Step 4.3 — Run Database Migrations
After containers start, in a new terminal:
```bash
docker compose exec api alembic upgrade head
```
If you get `alembic: command not found`, run:
```bash
docker compose exec api python -m alembic upgrade head
```

### Step 4.4 — Verify Each Service Manually

| Service | URL | What to Check |
|---------|-----|--------------|
| FastAPI docs | http://localhost:8000/docs | All endpoints visible |
| Streamlit UI | http://localhost:8501 | Dashboard loads |
| MinIO Console | http://localhost:9001 | Login: minioadmin/minioadmin |
| ChromaDB | http://localhost:8001/api/v1/heartbeat | Returns `{"nanosecond heartbeat": ...}` |

### Step 4.5 — Test the Pipeline via API
Open http://localhost:8000/docs and try:

```
POST /api/v1/pipeline/start
Body: {
  "user_id": "test-user-1",
  "query": "AI ML engineer internship India",
  "location": "India"
}
```
You should get back a `task_id`. Then poll:
```
GET /api/v1/tasks/{task_id}/status
```
Until status shows `SUCCESS`.

---

## PHASE 5 — Cover the Gaps, Hit 70%
> ⏱️ Est. Time: 2–3 days  
> 🎯 Goal: Coverage from 48% → 70%+

### Step 5.1 — Run Coverage Report After Each Phase
```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```
Open `htmlcov/index.html` in browser for a visual map of what's untested.

### Step 5.2 — Priority Files to Test Next

Work through these in order — each one gives the biggest coverage jump:

```
1. app/tasks/agent_tasks.py      (15% → target 60%)
2. app/api/v1/applications.py    (19% → target 65%)
3. app/llm/client.py             (17% → target 50%)
4. app/agents/nodes/generate.py  (24% → target 60%)
5. app/scrapers/serpapi.py       (0%  → target 80%)
```

### Step 5.3 — Add `pytest.ini` to Clean Up Output
Create `pytest.ini` in your project root:
```ini
[pytest]
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
addopts = --cov=app --cov-report=term-missing
```

---

## PHASE 6 — Deploy Live (Hugging Face Spaces)
> ⏱️ Est. Time: 1–2 days  
> 🎯 Goal: Live URL you can share with recruiters

### Step 6.1 — Create Hugging Face Account
Go to **https://huggingface.co** → Sign up → Create new Space → Choose **Docker** template

### Step 6.2 — Add a `README.md` to Your Space
```markdown
---
title: Rozgaar AI
emoji: 💼
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
```

### Step 6.3 — Push Your Project
```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/rozgaar-ai
git push hf main
```

### Step 6.4 — Add Secrets in HF Space Settings
In your Space → Settings → Variables and Secrets, add all your `.env` values one by one. Never commit `.env` to git.

---

## Daily Checklist

Use this every time you sit down to work:

```
[ ] Run pytest — all previous tests still passing?
[ ] Which phase am I on?
[ ] What is the ONE file I'm working on today?
[ ] Did I write the test BEFORE or AFTER the implementation?
[ ] Did I run docker compose up and check logs?
[ ] Did I commit my changes to git?
```

---

## Coverage Milestones

| Milestone | Coverage | Meaning |
|-----------|----------|---------|
| ✅ Now | 48% | Tests exist, core works |
| 🎯 After Phase 1–2 | ~58% | Scrapers + connections live |
| 🎯 After Phase 3 | ~68% | Pipeline tested end to end |
| 🎯 After Phase 5 | ~75% | Production-grade test suite |

---

## If You Get Stuck

| Problem | Where to Look |
|---------|--------------|
| Docker container won't start | `docker compose logs <service_name>` |
| Test fails with import error | Check virtual env: `myenv\Scripts\activate` |
| Alembic migration fails | Check `DATABASE_URL` in `.env` matches docker service name |
| LLM call fails | Check API key in `.env`, check rate limits |
| ChromaDB connection error | Make sure `CHROMA_URL=http://chroma:8000` not localhost |
| Redis connection error | Make sure `REDIS_URL=redis://redis:6379/0` not localhost |

> **Important:** Inside Docker, use service names (`postgres`, `redis`, `chroma`) not `localhost`. Outside Docker (running tests locally), use `localhost`.

---
