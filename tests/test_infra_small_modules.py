from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def test_get_checkpointer_uses_database_url():
    fake_saver = MagicMock()
    fake_module = types.ModuleType("langgraph.checkpoint.postgres")
    fake_module.PostgresSaver = SimpleNamespace(from_conn_string=fake_saver)

    sys.modules.pop("app.agents.checkpointer", None)
    settings = SimpleNamespace(database_url="postgresql://example")
    fake_saver.return_value = "saver"
    modules = {
        "langgraph.checkpoint.postgres": fake_module,
    }

    with patch.dict(sys.modules, modules):
        from app.agents import checkpointer

        with patch("app.agents.checkpointer.get_settings", return_value=settings):
            assert checkpointer.get_checkpointer() == "saver"

    fake_saver.assert_called_once_with("postgresql://example")


@pytest.mark.asyncio
async def test_placeholder_scrapers_return_empty_lists():
    from app.scrapers.indeed import IndeedScraper
    from app.scrapers.linkedin import LinkedInScraper
    from app.scrapers.naukri import NaukriScraper

    assert await IndeedScraper().search({"query": "AI"}) == []
    assert await LinkedInScraper().search({"query": "AI"}) == []
    assert await NaukriScraper().search({"query": "AI"}) == []


def test_chroma_client_builds_http_client_from_settings():
    from app.vector import client as vector_client

    fake_chromadb = SimpleNamespace(HttpClient=MagicMock(return_value="client"))

    with patch.dict(sys.modules, {"chromadb": fake_chromadb}), \
         patch.object(vector_client.settings, "chroma_url", "http://chroma.example:8123"):
        assert vector_client.get_chroma_client() == "client"

    fake_chromadb.HttpClient.assert_called_once_with(host="chroma.example", port=8123)


def test_chroma_client_reports_missing_dependency():
    from app.vector import client as vector_client

    with patch.dict(sys.modules, {"chromadb": None}):
        with pytest.raises(RuntimeError, match="chromadb is not installed"):
            vector_client.get_chroma_client()


def test_chroma_collections_create_expected_collections():
    from app.vector import collections

    fake_client = MagicMock()
    fake_client.get_or_create_collection.side_effect = ["jobs", "resumes", "skills"]

    with patch("app.vector.collections.get_chroma_client", return_value=fake_client):
        chroma = collections.ChromaCollections()

    assert chroma.job_embeddings == "jobs"
    assert chroma.resume_chunk_embeddings == "resumes"
    assert chroma.skill_taxonomy == "skills"
    assert fake_client.get_or_create_collection.call_count == 3


def test_minio_upload_file_puts_object_in_bucket():
    from app.storage import minio

    with patch("app.storage.minio.ensure_bucket") as mock_ensure, \
         patch.object(minio.client, "put_object") as mock_put:
        minio.upload_file("resume.pdf", b"pdf", content_type="application/pdf")

    mock_ensure.assert_called_once()
    args = mock_put.call_args.args
    assert args[1] == "resume.pdf"
    assert mock_put.call_args.kwargs == {"length": 3, "content_type": "application/pdf"}


def test_minio_download_file_reads_response():
    from app.storage import minio

    response = MagicMock()
    response.read.return_value = b"file-bytes"

    with patch.object(minio.client, "get_object", return_value=response) as mock_get:
        assert minio.download_file("resume.pdf") == b"file-bytes"

    assert mock_get.call_args.args[1] == "resume.pdf"
