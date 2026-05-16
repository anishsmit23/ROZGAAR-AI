from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.jobs import router as jobs_router
from app.api.v1.search import router as search_router
from app.db.models.agent_run import AgentRun
from app.db.models.application import Application, ApplicationState
from app.db.models.job_posting import JobPosting
from app.deps import get_current_user


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _ScalarResult(self._rows)

    def scalar_one(self):
        return self._rows[0]

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, store, user_ref):
        self.store = store
        self.user_ref = user_ref

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if isinstance(obj, AgentRun):
            self.store["runs"].append(obj)
        elif isinstance(obj, JobPosting):
            self.store["jobs"].append(obj)
        elif isinstance(obj, Application):
            self.store["applications"].append(obj)

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def execute(self, stmt):
        selected = stmt.column_descriptions[0]["entity"]
        if selected is AgentRun:
            return _Result(self.store["runs"])
        if selected is JobPosting:
            user_id = self.user_ref["current"].id
            rows = [
                job
                for job in self.store["jobs"]
                if job.user_id == user_id and job.semantic_score is not None
            ]
            rows.sort(key=lambda job: (job.semantic_score, job.discovered_at), reverse=True)
            return _Result(rows)
        return _Result([])


def test_ranked_jobs_are_scoped_to_authenticated_user():
    user_a = SimpleNamespace(id=uuid.uuid4(), email="a@example.com", is_active=True)
    user_b = SimpleNamespace(id=uuid.uuid4(), email="b@example.com", is_active=True)
    current_user = {"current": user_a}
    store = {"runs": [], "jobs": [], "applications": []}

    async def override_current_user():
        return current_user["current"]

    def fake_session_factory():
        return _AsyncSessionContext(_FakeSession(store, current_user))

    def fake_delay(user_id: str, query_params: dict, run_id: str):
        user_uuid = uuid.UUID(user_id)
        job = JobPosting(
            user_id=user_uuid,
            title="AI Engineer",
            company="Rozgaar Labs",
            location=query_params.get("location"),
            description="Build ranking systems",
            source="test",
            source_url="https://example.test/jobs/1",
            semantic_score=0.91,
        )
        job.id = uuid.uuid4()
        job.discovered_at = datetime.now(tz=timezone.utc)
        store["jobs"].append(job)

        application = Application(
            user_id=user_uuid,
            job_posting_id=job.id,
            state=ApplicationState.DISCOVERED,
            stage_number=1,
        )
        application.id = uuid.uuid4()
        store["applications"].append(application)
        return SimpleNamespace(id="task-user-a")

    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = override_current_user

    with patch("app.api.v1.search.async_session", side_effect=fake_session_factory), patch(
        "app.api.v1.jobs.async_session", side_effect=fake_session_factory
    ), patch("app.api.v1.search.run_job_search.delay", side_effect=fake_delay):
        client = TestClient(app)

        start_response = client.post(
            "/api/v1/pipeline/start",
            json={"query": "AI engineer", "location": "Remote", "remote": True, "limit": 1},
        )
        assert start_response.status_code == 200
        assert store["jobs"][0].user_id == user_a.id
        assert store["applications"][0].user_id == user_a.id

        current_user["current"] = user_b
        ranked_response = client.get("/api/v1/jobs/ranked")

    assert ranked_response.status_code == 200
    assert ranked_response.json() == []
