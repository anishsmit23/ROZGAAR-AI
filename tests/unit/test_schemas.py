"""Unit tests for schema validation."""

import pytest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.application import (
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
