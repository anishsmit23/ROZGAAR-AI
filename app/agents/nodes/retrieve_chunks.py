"""ChromaDB retrieval node - Fetch relevant chunks."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def retrieve_from_chroma(query: str, collection_name: str, n_results: int = 5, where_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    from app.deps import get_chroma
    try:
        chroma_client = get_chroma()
        collection = chroma_client.get_collection(name=collection_name)
        results = collection.query(query_texts=[query], n_results=n_results, where=where_filter, include=["documents", "metadatas", "distances"])
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        retrieved = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            retrieved.append({"document": doc, "metadata": metadata, "relevance_score": 1 - distance})
        logger.info(f"Retrieved {len(retrieved)} chunks from {collection_name}")
        return retrieved
    except Exception as e:
        logger.error(f"ChromaDB retrieval failed: {e}")
        return []


def retrieve_resume_chunks(user_id: str, n_results: int = 5) -> list[dict]:
    """Retrieve relevant resume chunks for a user."""
    return retrieve_from_chroma(query="resume experience skills achievements", collection_name=f"user_{user_id}_resume", n_results=n_results)


def retrieve_job_description_chunks(job_id: str, n_results: int = 5) -> list[dict]:
    """Retrieve relevant job description chunks."""
    return retrieve_from_chroma(query="job requirements skills responsibilities", collection_name="job_embeddings", n_results=n_results, where_filter={"job_id": job_id} if job_id else None)
