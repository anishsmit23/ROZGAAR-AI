"""Celery tasks for resume processing."""
from __future__ import annotations

import asyncio
import logging

from app.tasks.celery_app import celery_app
from app.vector.chroma_client import VectorStore

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30, queue="agents")
def embed_resume_background(self, user_id: str, resume_text: str) -> dict:
    """
    Background task to embed and store a user's resume in ChromaDB.
    
    Args:
        user_id: User UUID
        resume_text: Full resume text
    
    Returns:
        Status dict
    """
    try:
        vector_store = VectorStore()
        vector_store.embed_and_store_resume(user_id, resume_text)
        logger.info(f"Successfully embedded resume for user {user_id}")
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        logger.error(f"Error embedding resume for user {user_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=30)
