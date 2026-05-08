from unittest.mock import MagicMock, patch

import pytest

from app.tasks import agent_tasks


def test_run_job_search_success():
    with patch("app.tasks.agent_tasks.asyncio.run", return_value={"jobs_discovered": 1}):
        out = agent_tasks.run_job_search.run("00000000-0000-0000-0000-000000000000", {"query": "AI"}, "11111111-1111-1111-1111-111111111111")
        assert out["jobs_discovered"] == 1


def test_run_resume_tailor_success():
    with patch("app.tasks.agent_tasks.asyncio.run", return_value={"status": "completed"}):
        out = agent_tasks.run_resume_tailor.run("00000000-0000-0000-0000-000000000000", "22222222-2222-2222-2222-222222222222", "33333333-3333-3333-3333-333333333333")
        assert out["status"] == "completed"


def test_run_email_generation_success():
    with patch("app.tasks.agent_tasks.asyncio.run", return_value={"status": "completed"}):
        out = agent_tasks.run_email_generation.run("00000000-0000-0000-0000-000000000000", "22222222-2222-2222-2222-222222222222", "33333333-3333-3333-3333-333333333333")
        assert out["status"] == "completed"
