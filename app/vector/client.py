from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.config import get_settings

settings = get_settings()


def get_chroma_client() -> Any:
    try:
        import chromadb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "chromadb is not installed. Install project dependencies with Chroma support "
            "or run this service in Docker."
        ) from exc

    parsed = urlparse(settings.chroma_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    return chromadb.HttpClient(host=host, port=port)
