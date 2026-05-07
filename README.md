# Rozgaar AI Job Agent

Rozgaar AI is an asynchronous multi-agent pipeline for job discovery, semantic ranking, resume customization, cold email generation, and application tracking.

The repository is now aligned to `trdsrd.md`: FastAPI is the API gateway, Celery + Redis run background work, PostgreSQL stores the source of truth, ChromaDB stores embeddings, MinIO stores generated files, and Streamlit provides a lightweight local UI.

## Runtime Architecture

```text
Streamlit UI -> FastAPI -> Celery worker -> Agent pipeline
                    |            |
                    v            v
              PostgreSQL     Redis
              ChromaDB       MinIO
```

## Application Stages

```text
1 DISCOVERED -> 2 RANKED -> 3 RESUME_CUSTOMIZED -> 4 EMAIL_GENERATED
              -> 5 APPLIED -> 6 ACKNOWLEDGED -> 7 INTERVIEW_SCHEDULED -> 8 CLOSED
```

Every transition is recorded in `application_stage_transitions`.

## Core Data Model

- `users`: profile, preferences, skills, resume path, and resume text
- `job_postings`: discovered listings, source URL, embedding id, and semantic score
- `applications`: current stage, generated resume path, and email draft
- `application_stage_transitions`: timestamped stage history
- `agent_runs`: task/run metadata
- `agent_events`: append-only agent execution log

## API

All product APIs are under `/api/v1`.

- `POST /api/v1/pipeline/start`
- `GET /api/v1/jobs/ranked`
- `POST /api/v1/resume/customize`
- `POST /api/v1/email/generate`
- `GET /api/v1/applications/`
- `PATCH /api/v1/applications/{id}/stage`
- `GET /api/v1/tasks/{task_id}/status`
- `GET /health`

Auth routes are still provided by FastAPI Users:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/jwt/login`

## Repository Layout

```text
app/
  api/v1/          FastAPI routes
  auth/            FastAPI Users integration
  db/models/       SQLAlchemy persistence model
  agents/          LangGraph graph and node scaffolding
  tasks/           Celery tasks
  vector/          ChromaDB client/collections
  storage/         MinIO client
  scrapers/        Job source adapters
ui/                Streamlit dashboard
alembic/           Database migration
tests/             Smoke tests for API wiring and stage model
```

## Local Development

1. Copy `.env.example` to `.env` and fill secrets.
2. Start the stack:

```bash
docker compose up --build
```

3. Apply migrations:

```bash
docker compose run --rm api alembic upgrade head
```

4. Open:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:8501`
- MinIO Console: `http://localhost:9001`

## Notes

The current Celery tasks include deterministic stubs that create a sample discovered job, mark resume customization complete, and generate a placeholder email draft. They preserve the TRD workflow and persistence contracts while leaving real scraper, RAG, and document generation internals ready to fill in next.
