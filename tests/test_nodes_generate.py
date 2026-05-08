from unittest.mock import patch, MagicMock

import pytest

from app.agents.nodes import generate


def test_generate_tailored_resume_calls_llm():
    mock_client = MagicMock()
    mock_client.invoke.return_value = "Tailored resume content"

    with patch("app.agents.nodes.generate.get_llm_client", return_value=mock_client):
        out = generate.generate_tailored_resume(
            job_description="AI Engineer role",
            original_resume="Candidate resume text",
            highlighted_sections="Skills: Python, ML",
        )
        assert out == "Tailored resume content"


def test_generate_with_missing_template_var_raises():
    mock_client = MagicMock()
    mock_client.invoke.return_value = "irrelevant"

    with patch("app.agents.nodes.generate.get_llm_client", return_value=mock_client):
        with pytest.raises(ValueError):
            # template expects 'foo' which is not provided
            generate.generate_with_llm("Hello {foo}", {}, temperature=0.1)
