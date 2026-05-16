"""Unit tests for schema validation."""

import pytest
from types import SimpleNamespace
from uuid import uuid4
from pydantic import ValidationError
from app.db.models.application import ApplicationState
from app.schemas.application import (
    ApplicationRead,
    ResumeCustomizeRequest,
    EmailGenerateRequest,
    ApplicationStageUpdate,
)
from app.schemas.job import JobSearchRequest


@pytest.mark.unit
def test_resume_customize_request_valid():
    """Test valid resume customize request."""
    job_id = uuid4()
    req = ResumeCustomizeRequest(job_id=str(job_id))
    assert str(req.job_id) == str(job_id)


@pytest.mark.unit
def test_resume_customize_request_invalid_uuid():
    """Test invalid UUID raises validation error."""
    with pytest.raises(ValidationError):
        ResumeCustomizeRequest(job_id="not-a-uuid")


@pytest.mark.unit
def test_email_generate_request_valid():
    """Test valid email generate request."""
    app_id = uuid4()
    req = EmailGenerateRequest(application_id=str(app_id))
    assert str(req.application_id) == str(app_id)


@pytest.mark.unit
def test_application_stage_update():
    """Test application stage update."""
    update = ApplicationStageUpdate(
        stage="APPLIED",
        note="User submitted application"
    )
    assert update.stage == "APPLIED"
    assert update.note == "User submitted application"


@pytest.mark.unit
def test_job_search_request():
    """Test job search request validation."""
    req = JobSearchRequest(
        query="Python Developer",
        location="San Francisco",
        remote=True,
        limit=25
    )
    assert req.query == "Python Developer"
    assert req.remote is True
    assert req.limit == 25


@pytest.mark.unit
def test_application_read_accepts_uuid_orm_attributes():
    """Application responses should validate ORM UUID columns directly."""
    application = SimpleNamespace(
        id=uuid4(),
        job_posting_id=uuid4(),
        state=ApplicationState.DISCOVERED,
        stage_number=1,
        resume_version_path=None,
        email_draft=None,
        created_at=None,
        updated_at=None,
    )

    response = ApplicationRead.model_validate(application, from_attributes=True)

    assert response.id == application.id
    assert response.job_posting_id == application.job_posting_id
