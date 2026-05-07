from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.nodes import generate
from app.llm import client as llm_client


def test_generate_with_llm_success():
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = "done"

    with patch("app.agents.nodes.generate.get_llm_client", return_value=fake_llm):
        result = generate.generate_with_llm("Hello {name}", {"name": "Anish"}, temperature=0.4)

    assert result == "done"
    fake_llm.invoke.assert_called_once_with(
        prompt="Hello Anish",
        temperature=0.4,
        streaming=False,
    )


def test_generate_with_llm_retries_then_succeeds():
    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = [RuntimeError("temporary"), "recovered"]

    with patch("app.agents.nodes.generate.get_llm_client", return_value=fake_llm):
        result = generate.generate_with_llm("Hello", {}, max_retries=2)

    assert result == "recovered"
    assert fake_llm.invoke.call_count == 2


def test_generate_with_llm_missing_template_var():
    with pytest.raises(ValueError, match="Missing template variable"):
        generate.generate_with_llm("Hello {name}", {})


def test_generate_with_llm_exhausts_retries():
    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = RuntimeError("offline")

    with patch("app.agents.nodes.generate.get_llm_client", return_value=fake_llm):
        with pytest.raises(RuntimeError, match="LLM failed after"):
            generate.generate_with_llm("Hello", {}, max_retries=2)


def test_generate_structured_success():
    fake_llm = MagicMock()
    fake_llm.invoke_structured.return_value = {"title": "AI Engineer"}

    with patch("app.agents.nodes.generate.get_llm_client", return_value=fake_llm):
        result = generate.generate_structured("Job {id}", {"id": 1}, dict)

    assert result == {"title": "AI Engineer"}
    fake_llm.invoke_structured.assert_called_once()


def test_generate_structured_missing_template_var():
    with pytest.raises(ValueError, match="Missing template variable"):
        generate.generate_structured("Job {id}", {}, dict)


def test_specialized_generators_delegate_to_generate_with_llm():
    with patch("app.agents.nodes.generate.generate_with_llm", return_value="generated") as mock_generate:
        assert generate.generate_tailored_resume("jd", "resume", "sections") == "generated"
        assert generate.generate_email_to_recruiter(job_description="jd", resume_context="ctx") == "generated"
        assert generate.generate_email_to_recruiter(job_title="Engineer") == "generated"
        assert generate.generate_interview_questions("Role", "Co", "JD", "BG") == "generated"
        assert generate.generate_model_answer("BG", "Question") == "generated"

    assert mock_generate.call_count == 5


def test_llm_client_prefers_groq_client():
    fake_groq = MagicMock(name="groq")
    fake_openai = MagicMock(name="openai")

    with patch("app.llm.client.ChatGroq", return_value=fake_groq), \
         patch("app.llm.client.ChatOpenAI", return_value=fake_openai):
        client = llm_client.LLMClient(use_groq=True)
        assert client.client is fake_groq


def test_llm_client_falls_back_to_openai_when_groq_unavailable():
    fake_openai = MagicMock(name="openai")

    with patch("app.llm.client.ChatGroq", side_effect=RuntimeError("bad groq")), \
         patch("app.llm.client.ChatOpenAI", return_value=fake_openai):
        client = llm_client.LLMClient(use_groq=True)
        assert client.client is fake_openai


def test_llm_client_raises_when_no_clients_available():
    with patch("app.llm.client.ChatGroq", side_effect=RuntimeError("bad groq")), \
         patch("app.llm.client.ChatOpenAI", side_effect=RuntimeError("bad openai")):
        client = llm_client.LLMClient()
        with pytest.raises(RuntimeError, match="No LLM client available"):
            _ = client.client


def test_llm_invoke_returns_response_content():
    response = SimpleNamespace(content="hello")
    runnable = MagicMock()
    runnable.with_config.return_value = runnable
    runnable.invoke.return_value = response

    client = llm_client.LLMClient()
    client._clients_initialized = True
    client._groq_client = runnable

    result = client.invoke("Say hi", system_prompt="system", temperature=0.1)

    assert result == "hello"
    runnable.with_config.assert_called_once_with({"temperature": 0.1})
    runnable.invoke.assert_called_once()


def test_llm_invoke_structured_supports_model_dump():
    structured_response = MagicMock()
    structured_response.model_dump.return_value = {"ok": True}
    structured_client = MagicMock()
    structured_client.invoke.return_value = structured_response
    runnable = MagicMock()
    runnable.with_structured_output.return_value = structured_client

    client = llm_client.LLMClient(use_groq=False)
    client._clients_initialized = True
    client._openai_client = runnable

    assert client.invoke_structured("Prompt", dict) == {"ok": True}


def test_llm_batch_invoke_returns_contents():
    runnable = MagicMock()
    runnable.batch.return_value = [SimpleNamespace(content="a"), SimpleNamespace(content="b")]
    client = llm_client.LLMClient()
    client._clients_initialized = True
    client._groq_client = runnable

    assert client.batch_invoke(["one", "two"]) == ["a", "b"]


def test_llm_retry_with_fallback_uses_openai_after_groq_failure():
    client = llm_client.LLMClient()
    client._clients_initialized = True
    client._groq_client = MagicMock()
    client._openai_client = MagicMock()

    with patch.object(client, "invoke", side_effect=[RuntimeError("groq down"), "fallback ok"]):
        assert client.retry_with_fallback("Prompt") == "fallback ok"
        assert client.use_groq is False


def test_get_llm_client_reuses_singleton():
    with patch("app.llm.client.LLMClient") as mock_cls:
        llm_client._llm_client_instance = None
        first = llm_client.get_llm_client()
        second = llm_client.get_llm_client()

    assert first is second
    mock_cls.assert_called_once()
    llm_client._llm_client_instance = None
