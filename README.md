# Rozgaar AI

![Python](https://img.shields.io/badge/python-3.11-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![Coverage](https://img.shields.io/badge/coverage-73%25-green)
![License](https://img.shields.io/badge/license-not%20specified-lightgrey)

Rozgaar AI is an async job-application pipeline that discovers jobs, ranks them against a user's resume, generates tailored application assets, and tracks each opportunity through a structured state machine. It is built as a backend-heavy portfolio project: FastAPI exposes the product API, Celery workers run long-running agent tasks, PostgreSQL stores durable state, ChromaDB stores resume embeddings, MinIO/S3 stores generated files, and LangGraph is used to model the multi-agent workflow. The system is not pretending to be a finished SaaS product; it is a working architecture for the hard parts of an AI job agent: auth, async orchestration, persistence, vector search, file generation, and auditable state transitions.

## How It Works

Rozgaar starts with a user account and a resume. The resume is uploaded as a PDF, parsed into text, stored on the user record, and embedded into a per-user ChromaDB collection. That collection becomes the user's private semantic profile for later job ranking.

When the user starts a search, FastAPI creates an `AgentRun` and queues a Celery task instead of doing the work inside the request cycle. The worker asks the job discovery layer for listings, currently through Adzuna with fallback support for other sources. Those raw listings are normalized, scored against the user's resume embeddings, and persisted as `JobPosting` rows linked to that authenticated user.

The agent split is intentionally close to how the product behaves. The Orchestrator agent owns the run lifecycle and hands work to specialized agents: Job Discovery fetches and normalizes listings, Ranking compares those listings with the user's resume embeddings, Resume generates a role-specific resume artifact, Email drafts outreach, and Tracker records the user's progress through the application state machine. This keeps the workflow easy to reason about when one step fails, retries, or needs to be replaced.

From there, each opportunity moves through an 8-stage application pipeline:

1. `DISCOVERED` means the system found a job and created an application record for it.
2. `RANKED` means the job has been evaluated against the user's resume and has a semantic relevance score.
3. `RESUME_CUSTOMIZED` means a resume-tailoring task has generated a role-specific resume version.
4. `EMAIL_GENERATED` means the email agent has drafted a cold outreach or application email.
5. `APPLIED` means the user has submitted the application or marked it as submitted.
6. `ACKNOWLEDGED` means the employer has confirmed receipt or responded.
7. `INTERVIEW_SCHEDULED` means the opportunity has moved into interview coordination.
8. `CLOSED` means the application is no longer active, either because it ended successfully, was rejected, or the user closed it manually.

Every stage transition is recorded in `application_stage_transitions`, so the current state is fast to read from `applications`, while the history remains available for debugging, analytics, and future agent evaluation. The design keeps the agents practical: discovery, ranking, resume generation, email generation, and tracking can fail or retry independently without corrupting the user's application state.

## Technical Decisions

### LangGraph for Agent Orchestration

LangGraph is a better fit than a single prompt chain because the workflow has explicit state, conditional routing, and separate responsibilities. Job discovery, ranking, resume generation, email drafting, and tracking are not just prompt steps; they are nodes with inputs, outputs, failure modes, and persistence boundaries. LangGraph gives the project a clear place to model those transitions without hiding control flow inside one large function.

### Celery + Redis Over FastAPI BackgroundTasks

FastAPI `BackgroundTasks` are useful for short local side effects, but this pipeline needs durable task execution, retries, separate worker processes, and observable task IDs. Celery + Redis lets API requests return quickly while workers handle scraper latency, vector scoring, LLM calls, PDF generation, and S3 uploads. It also makes the system easier to scale: API containers and worker containers can be sized independently.

### ChromaDB for Vector Search

ChromaDB is used because the ranking problem is embedding-first and local-development friendly. The system stores resume chunks by user and queries them against job descriptions to produce semantic scores. A full managed vector database would be reasonable later, but Chroma keeps the portfolio version reproducible in Docker Compose and simple enough to inspect.

### Groq Over OpenAI

Groq is used for the LLM path because it gives fast inference on open models like `llama3-70b`, which is a good tradeoff for iterative agent workflows where latency matters. The code is structured so the LLM client can be swapped or extended, but Groq keeps local demos responsive without designing the whole project around one closed provider.

### 8-Stage State Machine

The application pipeline is modeled as explicit stages instead of free-form status strings because the system needs reliable automation boundaries. A resume agent should not run on a closed application; an email agent should only run after a job is ranked or a resume is customized; manual tracking should still fit the same state history. The state machine gives the backend predictable validation and gives future analytics a clean event trail.

## Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| API gateway | FastAPI | Authenticated HTTP API, request validation, task kickoff, status reads |
| Auth | FastAPI Users + JWT | User registration, login, bearer-token protection, per-user data scoping |
| Orchestration | LangGraph | Multi-agent workflow modeling with explicit state and node boundaries |
| Async execution | Celery | Long-running agent work, retries, task status, worker isolation |
| Broker/result backend | Redis | Celery message broker, task result backend, lightweight status streaming |
| Database | PostgreSQL | Source of truth for users, jobs, applications, runs, and transitions |
| ORM/migrations | SQLAlchemy + Alembic | Typed async data access and repeatable schema changes |
| Vector search | ChromaDB | Per-user resume embeddings and semantic job ranking |
| File storage | MinIO / S3 | Generated resume PDFs and future application artifacts |
| Job source | Adzuna API | Job discovery provider for real external listings |
| LLM | Groq `llama3-70b` | Resume customization and cold-email generation |
| UI | Streamlit / frontend container | Local operator dashboard and demo surface |
| Packaging | Docker Compose | Reproducible local stack with API, worker, database, vector store, Redis, and storage |

## Setup

These commands assume Docker Desktop and OpenSSL are installed.

### 1. Clone and enter the repo

```bash
git clone <your-repo-url> rozgaar-ai
cd rozgaar-ai
```

### 2. Create environment files and JWT keys

```bash
cp .env.example .env
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

Edit `.env` and set at least:

```env
DATABASE_URL=postgresql+asyncpg://rozgaar:rozgaar@postgres:5432/rozgaar
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
SECRET_KEY=replace-with-at-least-32-characters
GROQ_API_KEY=your_groq_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
JWT_PRIVATE_KEY_FILE=/app/private_key.pem
JWT_PUBLIC_KEY_FILE=/app/public_key.pem
CHROMA_HOST=http://chroma:8000
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
```

### 3. Build and start the stack

```bash
docker compose up --build -d
```

### 4. Apply database migrations

```bash
docker compose run --rm api alembic upgrade head
```

### 5. Open the app surfaces

```bash
docker compose ps
```

Then open:

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Frontend container: `http://localhost:3000`
- MinIO console: `http://localhost:9001`
- ChromaDB HTTP port: `http://localhost:8001`

## API Reference

All product endpoints are under `/api/v1`. Authenticated endpoints require:

```http
Authorization: Bearer <access_token>
```

### Register User

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/auth/register` |
| Auth | No |

Request:

```json
{
  "email": "candidate@example.com",
  "password": "StrongPassword123!",
  "full_name": "Candidate Name",
  "skills": ["Python", "FastAPI", "SQL"],
  "experience_years": 2,
  "preferences": {
    "remote": true,
    "locations": ["Remote", "Bengaluru"]
  }
}
```

Response:

```json
{
  "id": "7f8b8a32-4d4e-4d67-8f5f-2b7a2b96d111",
  "email": "candidate@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "full_name": "Candidate Name",
  "skills": ["Python", "FastAPI", "SQL"],
  "experience_years": 2,
  "resume_path": null,
  "preferences": {
    "remote": true,
    "locations": ["Remote", "Bengaluru"]
  }
}
```

### Login

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/auth/jwt/login` |
| Auth | No |
| Content type | `application/x-www-form-urlencoded` |

Request:

```text
username=candidate@example.com&password=StrongPassword123!
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

### Upload Resume

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/resume/upload` |
| Auth | Required |
| Content type | `multipart/form-data` |

Request:

```bash
curl -X POST http://localhost:8000/api/v1/resume/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@resume.pdf"
```

Response:

```json
{
  "status": "success",
  "message": "Resume uploaded and queued for processing",
  "filename": "resume.pdf",
  "chars": 4821
}
```

### Start Job Search Pipeline

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/pipeline/start` |
| Auth | Required |

Request:

```json
{
  "query": "backend engineering intern",
  "location": "Bengaluru",
  "remote": true,
  "limit": 10
}
```

Response:

```json
{
  "task_id": "0d83b6aa-cf4e-4f84-aab2-3793f2c77421",
  "run_id": "f740df27-c102-49b1-8e02-674d3ac7d5aa"
}
```

### Get Task Status

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/tasks/{task_id}/status` |
| Alias | `/api/v1/tasks/{task_id}` |
| Auth | Required |

Request body: none.

Response:

```json
{
  "task_id": "0d83b6aa-cf4e-4f84-aab2-3793f2c77421",
  "state": "SUCCESS",
  "status": "SUCCESS",
  "result": {
    "completed_at": "2026-05-16T09:30:00+00:00",
    "jobs_discovered": 7
  },
  "error": null,
  "application_id": null,
  "stage": null
}
```

### Stream Task Status

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/tasks/{task_id}/stream` |
| Auth | Required |

Request body: none.

Response is Server-Sent Events:

```text
data: {"state":"SUCCESS","stage":"DISCOVERED","application_id":null,"error":null}
```

### List Jobs

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/jobs?company=Acme&limit=50&offset=0` |
| Auth | Required |

Request body: none.

Response:

```json
[
  {
    "id": "a39fcf03-2e5e-4af6-a68e-d9317d6ad447",
    "title": "Backend Engineering Intern",
    "company": "Acme",
    "location": "Remote",
    "source": "adzuna",
    "source_url": "https://example.com/job/123",
    "semantic_score": 0.86,
    "discovered_at": "2026-05-16T09:30:00Z"
  }
]
```

### List Ranked Jobs

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/jobs/ranked?limit=50&offset=0` |
| Auth | Required |

Request body: none.

Response:

```json
[
  {
    "id": "a39fcf03-2e5e-4af6-a68e-d9317d6ad447",
    "title": "Backend Engineering Intern",
    "company": "Acme",
    "location": "Remote",
    "source": "adzuna",
    "source_url": "https://example.com/job/123",
    "semantic_score": 0.86,
    "discovered_at": "2026-05-16T09:30:00Z"
  }
]
```

### Customize Resume

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/resume/customize` |
| Auth | Required |

Request:

```json
{
  "job_id": "a39fcf03-2e5e-4af6-a68e-d9317d6ad447"
}
```

Response:

```json
{
  "application_id": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39",
  "task_id": "c25e94d5-425b-47e9-bec7-bb065f0f196a"
}
```

### Generate Email

| Field | Value |
| --- | --- |
| Method | `POST` |
| Path | `/api/v1/email/generate` |
| Auth | Required |

Request:

```json
{
  "application_id": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39"
}
```

Response:

```json
{
  "application_id": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39",
  "task_id": "b0203c2e-340d-48aa-9c1f-9a4bd9f89f9c"
}
```

### List Applications

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/applications?state=DISCOVERED&limit=50&offset=0` |
| Alias | `/api/v1/applications/` |
| Auth | Required |

Request body: none.

Response:

```json
[
  {
    "id": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39",
    "job_posting_id": "a39fcf03-2e5e-4af6-a68e-d9317d6ad447",
    "state": "DISCOVERED",
    "stage_number": 1,
    "resume_version_path": null,
    "email_draft": null,
    "created_at": "2026-05-16T09:30:00Z",
    "updated_at": "2026-05-16T09:30:00Z"
  }
]
```

### Update Application Stage

| Field | Value |
| --- | --- |
| Method | `PATCH` |
| Path | `/api/v1/applications/{application_id}/stage` |
| Auth | Required |

Request:

```json
{
  "stage": "APPLIED",
  "note": "Submitted through company careers page"
}
```

Response:

```json
{
  "id": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39",
  "job_posting_id": "a39fcf03-2e5e-4af6-a68e-d9317d6ad447",
  "state": "APPLIED",
  "stage_number": 5,
  "resume_version_path": "6e52ea7e-95c8-4f0c-b3e7-2c50a2f8cc39/resume_v1.pdf",
  "email_draft": "Hi...",
  "created_at": "2026-05-16T09:30:00Z",
  "updated_at": "2026-05-16T10:12:00Z"
}
```

### Download Generated Resume

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/applications/{application_id}/resume/download` |
| Auth | Required |

Request body: none.

Response:

```json
{
  "download_url": "http://localhost:9000/generated-resumes/6e52.../resume_v1.pdf?X-Amz-Algorithm=..."
}
```

### Latest RAG Evaluation

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/api/v1/evaluations/latest` |
| Auth | Required |

Request body: none.

Response:

```json
{
  "id": "efc49114-01ce-486a-96e3-631f277f4de8",
  "user_id": "7f8b8a32-4d4e-4d67-8f5f-2b7a2b96d111",
  "evaluated_at": "2026-05-16T10:30:00Z",
  "context_precision": 0.78,
  "context_recall": 0.64,
  "sample_size": 10
}
```

### Health Check

| Field | Value |
| --- | --- |
| Method | `GET` |
| Path | `/health` |
| Auth | No |

Request body: none.

Response:

```json
{
  "status": "ok"
}
```

## Roadmap

- **Playwright auto-apply:** use browser automation for controlled application submission on job boards that do not expose APIs, with human confirmation before final submit.
- **LinkedIn integration:** import profile context, discover matching roles, and track LinkedIn-originated opportunities separately from Adzuna results.
- **RAGAS evaluation:** expand the existing evaluation path into scheduled ranking-quality checks that compare retrieved resume context against generated rankings and application outcomes.
- **React frontend:** replace the local dashboard/demo surface with a production-quality React interface for search, pipeline status, application tracking, and generated artifact review.
- **Better agent observability:** expose agent events and graph traces in the UI so failures are explainable without reading worker logs.

## Repository Layout

```text
app/
  api/v1/          FastAPI routes
  auth/            FastAPI Users integration
  db/models/       SQLAlchemy models for users, jobs, applications, runs, events
  agents/          LangGraph graphs, nodes, prompts, and LLM client
  tasks/           Celery tasks for search, resume, email, evaluation
  vector/          ChromaDB client and collection helpers
  storage/         MinIO/S3 file storage
  scrapers/        Job source adapters
alembic/           Database migrations
tests/             Unit and integration tests
ui/                Streamlit dashboard
frontend/          Containerized web frontend
```

## Engineering Notes

- Job, application, task, and evaluation reads are scoped to the authenticated user.
- Resume embeddings are stored in per-user Chroma collections named `resumes_{user_id}`.
- Generated files are stored out of the database; the DB keeps only object paths and metadata.
- Celery task IDs are returned immediately so clients can poll or stream status while workers continue execution.
- The current implementation is optimized for a clear, reviewable backend architecture over UI polish.
