from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import applications
from app.db.models.application import ApplicationState


class AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.mark.asyncio
async def test_list_applications_rejects_invalid_state():
    with pytest.raises(HTTPException) as exc:
        await applications.list_applications(state="not-a-stage", user=user())

    assert exc.value.status_code == 422
    assert "Invalid state" in exc.value.detail


@pytest.mark.asyncio
async def test_list_applications_returns_session_results():
    app = SimpleNamespace(id=uuid.uuid4())
    scalars = MagicMock()
    scalars.all.return_value = [app]
    result = MagicMock()
    result.scalars.return_value = scalars
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    with patch("app.api.v1.applications.async_session", return_value=AsyncSessionContext(session)):
        assert await applications.list_applications(limit=50, offset=0, user=user()) == [app]

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_applications_wraps_database_error():
    session = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("db down")))

    with patch("app.api.v1.applications.async_session", return_value=AsyncSessionContext(session)):
        with pytest.raises(HTTPException) as exc:
            await applications.list_applications(limit=50, offset=0, user=user())

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_application_stage_success():
    current_user = user()
    application = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        state=ApplicationState.DISCOVERED,
        stage_number=1,
    )
    session = SimpleNamespace(
        get=AsyncMock(return_value=application),
        add=MagicMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    payload = SimpleNamespace(stage="applied", note="Submitted manually")

    with patch("app.api.v1.applications.async_session", return_value=AsyncSessionContext(session)):
        result = await applications.update_application_stage(application.id, payload, current_user)

    assert result is application
    assert application.state == ApplicationState.APPLIED
    assert application.stage_number == 5
    transition = session.add.call_args.args[0]
    assert transition.from_state == ApplicationState.DISCOVERED
    assert transition.to_state == ApplicationState.APPLIED
    assert transition.note == "Submitted manually"


@pytest.mark.asyncio
async def test_update_application_stage_rejects_unknown_stage():
    with pytest.raises(HTTPException) as exc:
        await applications.update_application_stage(
            uuid.uuid4(),
            SimpleNamespace(stage="unknown", note=None),
            user(),
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_application_stage_404_for_wrong_user():
    current_user = user()
    application = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    session = SimpleNamespace(get=AsyncMock(return_value=application))

    with patch("app.api.v1.applications.async_session", return_value=AsyncSessionContext(session)):
        with pytest.raises(HTTPException) as exc:
            await applications.update_application_stage(application.id, SimpleNamespace(stage="closed"), current_user)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_tailor_resume_rejects_invalid_job_id():
    with pytest.raises(HTTPException) as exc:
        await applications.tailor_resume(SimpleNamespace(job_id="bad-id"), user())

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_generate_email_rejects_invalid_application_id():
    with pytest.raises(HTTPException) as exc:
        await applications.generate_email(SimpleNamespace(application_id="bad-id"), user())

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_generate_email_rejects_wrong_state():
    current_user = user()
    application = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        state=ApplicationState.DISCOVERED,
    )
    session = SimpleNamespace(get=AsyncMock(return_value=application))

    with patch("app.api.v1.applications.async_session", return_value=AsyncSessionContext(session)):
        with pytest.raises(HTTPException) as exc:
            await applications.generate_email(SimpleNamespace(application_id=str(application.id)), current_user)

    assert exc.value.status_code == 409
