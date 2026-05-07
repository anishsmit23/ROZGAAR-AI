from __future__ import annotations

from app.config import get_settings


def get_checkpointer():
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langgraph-checkpoint-postgres is not installed. Install project dependencies "
            "or run this service in Docker."
        ) from exc

    settings = get_settings()
    return PostgresSaver.from_conn_string(settings.database_url)
