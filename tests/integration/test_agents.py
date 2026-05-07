"""Integration tests for agent graphs."""

import pytest
from app.agents.graphs.job_search import build_job_search_graph
from app.agents.graphs.resume_tailor import build_resume_tailor_graph
from app.agents.graphs.email_gen import build_email_generation_graph


@pytest.mark.integration
def test_job_search_graph_builds():
    """Test job search graph compiles without errors."""
    graph = build_job_search_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


@pytest.mark.integration
def test_resume_tailor_graph_builds():
    """Test resume tailor graph compiles without errors."""
    graph = build_resume_tailor_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


@pytest.mark.integration
def test_email_generation_graph_builds():
    """Test email generation graph compiles without errors."""
    graph = build_email_generation_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")
