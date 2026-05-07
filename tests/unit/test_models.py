"""Unit tests for database models."""

import pytest
from app.db.models.user import User
from app.db.models.application import Application, ApplicationState, APPLICATION_STAGE_ORDER
from app.db.models.job_posting import JobPosting


@pytest.mark.unit
def test_user_creation():
    """Test user model instantiation."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_here",
        is_active=True,
        is_verified=False
    )
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.is_verified is False


@pytest.mark.unit
def test_application_state_enum():
    """Test application state enum values."""
    assert ApplicationState.DISCOVERED.value == "DISCOVERED"
    assert ApplicationState.APPLIED.value == "APPLIED"
    assert ApplicationState.CLOSED.value == "CLOSED"


@pytest.mark.unit
def test_application_stage_order():
    """Test application stage ordering."""
    assert APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED] == 1
    assert APPLICATION_STAGE_ORDER[ApplicationState.RANKED] == 2
    assert APPLICATION_STAGE_ORDER[ApplicationState.RESUME_CUSTOMIZED] == 3
    assert APPLICATION_STAGE_ORDER[ApplicationState.EMAIL_GENERATED] == 4
    assert APPLICATION_STAGE_ORDER[ApplicationState.APPLIED] == 5
    assert APPLICATION_STAGE_ORDER[ApplicationState.ACKNOWLEDGED] == 6
    assert APPLICATION_STAGE_ORDER[ApplicationState.INTERVIEW_SCHEDULED] == 7
    assert APPLICATION_STAGE_ORDER[ApplicationState.CLOSED] == 8
