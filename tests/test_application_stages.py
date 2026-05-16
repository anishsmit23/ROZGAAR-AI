import pytest

from app.db.models.application import ApplicationStage


def test_all_9_stages_exist():
    stages = [s.value for s in ApplicationStage]
    assert len(stages) == 9
    assert ApplicationStage.FAILED.value == 9


def test_stage_progression_order():
    stage_values = [s.value for s in ApplicationStage]
    assert stage_values == sorted(stage_values)
