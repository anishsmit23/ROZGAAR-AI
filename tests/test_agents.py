"""Application model smoke tests."""

from __future__ import annotations

from app.db.models.application import APPLICATION_STAGE_ORDER, ApplicationState


def test_application_stage_order_matches_trd():
    assert APPLICATION_STAGE_ORDER[ApplicationState.DISCOVERED] == 1
    assert APPLICATION_STAGE_ORDER[ApplicationState.RANKED] == 2
    assert APPLICATION_STAGE_ORDER[ApplicationState.RESUME_CUSTOMIZED] == 3
    assert APPLICATION_STAGE_ORDER[ApplicationState.EMAIL_GENERATED] == 4
    assert APPLICATION_STAGE_ORDER[ApplicationState.APPLIED] == 5
    assert APPLICATION_STAGE_ORDER[ApplicationState.ACKNOWLEDGED] == 6
    assert APPLICATION_STAGE_ORDER[ApplicationState.INTERVIEW_SCHEDULED] == 7
    assert APPLICATION_STAGE_ORDER[ApplicationState.CLOSED] == 8
