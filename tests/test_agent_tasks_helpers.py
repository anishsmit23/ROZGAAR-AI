from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.application import ApplicationState
from app.tasks import agent_tasks


class AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FailingAsyncSessionContext:
    def __init__(self, exc: Exception):
        self.exc = exc

    async def __aenter__(self):
        raise self.exc

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_set_run_status_updates_output_and_error():
    run = SimpleNamespace(status="queued", output_snapshot=None)
    session = SimpleNamespace(
        get=AsyncMock(return_value=run),
        commit=AsyncMock(),
    )

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)):
        await agent_tasks._set_run_status(
            str(uuid.uuid4()),
            "failed",
            output={"step": "search"},
            error="boom",
        )

    assert run.status == "failed"
    assert run.output_snapshot == {"step": "search", "error": "boom"}
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_run_status_returns_when_run_missing():
    session = SimpleNamespace(
        get=AsyncMock(return_value=None),
        commit=AsyncMock(),
    )

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)):
        await agent_tasks._set_run_status(str(uuid.uuid4()), "running")

    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_log_event_adds_agent_event():
    session = SimpleNamespace(add=MagicMock(), commit=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)):
        await agent_tasks._log_event(
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "search_started",
            {"query": "AI"},
        )

    event = session.add.call_args.args[0]
    assert event.step_name == "search_started"
    assert event.payload == {"query": "AI"}
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_application_state_updates_stage_and_transition():
    application = SimpleNamespace(
        id=uuid.uuid4(),
        state=ApplicationState.DISCOVERED,
        stage_number=1,
    )
    session = SimpleNamespace(
        get=AsyncMock(return_value=application),
        add=MagicMock(),
        commit=AsyncMock(),
    )

    user_id = str(uuid.uuid4())
    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)):
        await agent_tasks._set_application_state(
            str(application.id),
            user_id,
            ApplicationState.EMAIL_GENERATED,
            "Email ready",
        )

    assert application.state == ApplicationState.EMAIL_GENERATED
    assert application.stage_number == 4
    transition = session.add.call_args.args[0]
    assert transition.from_state == ApplicationState.DISCOVERED
    assert transition.to_state == ApplicationState.EMAIL_GENERATED
    assert transition.note == "Email ready"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_application_state_returns_when_application_missing():
    session = SimpleNamespace(
        get=AsyncMock(return_value=None),
        add=MagicMock(),
        commit=AsyncMock(),
    )

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)):
        await agent_tasks._set_application_state(
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            ApplicationState.CLOSED,
        )

    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_set_run_status_handles_session_failure():
    with patch("app.tasks.agent_tasks.async_session", return_value=FailingAsyncSessionContext(RuntimeError("db down"))):
        await agent_tasks._set_run_status(str(uuid.uuid4()), "running")


@pytest.mark.asyncio
async def test_log_event_handles_session_failure():
    with patch("app.tasks.agent_tasks.async_session", return_value=FailingAsyncSessionContext(RuntimeError("db down"))):
        await agent_tasks._log_event(str(uuid.uuid4()), str(uuid.uuid4()), "search_started")


@pytest.mark.asyncio
async def test_set_application_state_handles_session_failure():
    with patch("app.tasks.agent_tasks.async_session", return_value=FailingAsyncSessionContext(RuntimeError("db down"))):
        await agent_tasks._set_application_state(str(uuid.uuid4()), str(uuid.uuid4()), ApplicationState.CLOSED)


def test_run_job_search_success_uses_session_and_status_helpers():
    user_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    session = SimpleNamespace(add=MagicMock(), commit=AsyncMock(), refresh=AsyncMock())

    async def refresh(obj):
        obj.id = uuid.uuid4()

    session.refresh.side_effect = refresh

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()) as mock_event:
        result = agent_tasks.run_job_search.run(
            user_id,
            {"query": "AI engineer", "location": "India"},
            run_id,
        )

    assert result["jobs_discovered"] == 1
    assert session.add.call_count == 3
    assert mock_event.await_count == 2
    assert mock_status.await_count == 2


def test_run_resume_tailor_success_updates_application():
    user_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    application = SimpleNamespace(resume_version_path=None)
    session = SimpleNamespace(get=AsyncMock(return_value=application), commit=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()) as mock_event, \
         patch("app.tasks.agent_tasks._set_application_state", new=AsyncMock()) as mock_state:
        result = agent_tasks.run_resume_tailor.run(
            user_id,
            application_id,
            run_id,
        )

    assert result == {"application_id": application_id, "status": "completed"}
    assert application.resume_version_path == f"minio://generated-resumes/{application_id}.pdf"
    assert mock_event.await_count == 2
    assert mock_state.await_args.args[2] == ApplicationState.RESUME_CUSTOMIZED
    assert mock_status.await_count == 2


def test_run_email_generation_success_updates_application():
    user_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    application = SimpleNamespace(email_draft=None)
    session = SimpleNamespace(get=AsyncMock(return_value=application), commit=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()) as mock_event, \
         patch("app.tasks.agent_tasks._set_application_state", new=AsyncMock()) as mock_state:
        result = agent_tasks.run_email_generation.run(
            user_id,
            application_id,
            run_id,
        )

    assert result == {"application_id": application_id, "status": "completed"}
    assert "interested in this role" in application.email_draft
    assert mock_event.await_count == 2
    assert mock_state.await_args.args[2] == ApplicationState.EMAIL_GENERATED
    assert mock_status.await_count == 2


def test_run_job_search_failure_triggers_retry_path():
    user_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    session = SimpleNamespace(add=MagicMock(side_effect=RuntimeError("db boom")), commit=AsyncMock(), refresh=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()), \
         patch.object(agent_tasks.run_job_search, "retry", side_effect=RuntimeError("retry called")) as mock_retry:
        with pytest.raises(RuntimeError, match="retry called"):
            agent_tasks.run_job_search.run(
                user_id,
                {"query": "AI engineer", "location": "India"},
                run_id,
            )

    assert mock_status.await_args.args[1] == "failed"
    assert mock_retry.called


def test_run_resume_tailor_missing_application_triggers_retry_path():
    user_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=None), commit=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()), \
         patch("app.tasks.agent_tasks._set_application_state", new=AsyncMock()), \
         patch.object(agent_tasks.run_resume_tailor, "retry", side_effect=RuntimeError("retry called")) as mock_retry:
        with pytest.raises(RuntimeError, match="retry called"):
            agent_tasks.run_resume_tailor.run(user_id, application_id, run_id)

    assert mock_status.await_args.args[1] == "failed"
    assert mock_retry.called


def test_run_email_generation_missing_application_triggers_retry_path():
    user_id = str(uuid.uuid4())
    application_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=None), commit=AsyncMock())

    with patch("app.tasks.agent_tasks.async_session", return_value=AsyncSessionContext(session)), \
         patch("app.tasks.agent_tasks._set_run_status", new=AsyncMock()) as mock_status, \
         patch("app.tasks.agent_tasks._log_event", new=AsyncMock()), \
         patch("app.tasks.agent_tasks._set_application_state", new=AsyncMock()), \
         patch.object(agent_tasks.run_email_generation, "retry", side_effect=RuntimeError("retry called")) as mock_retry:
        with pytest.raises(RuntimeError, match="retry called"):
            agent_tasks.run_email_generation.run(user_id, application_id, run_id)

    assert mock_status.await_args.args[1] == "failed"
    assert mock_retry.called
