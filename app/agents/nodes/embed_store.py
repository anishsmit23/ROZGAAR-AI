"""Embed and store node - ChromaDB embedding + storage."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def embed_and_store(documents: list[str], collection_name: str, metadatas: list[dict[str, Any]] | None = None, ids: list[str] | None = None) -> bool:
    from app.deps import get_chroma
    if not documents:
        logger.warning("No documents to embed")
        return False
    try:
        chroma_client = get_chroma()
        collection = chroma_client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        collection.add(documents=documents, metadatas=metadatas or [{} for _ in documents], ids=ids or [f"{collection_name}_{i}" for i in range(len(documents))])
        logger.info(f"Embedded {len(documents)} documents in {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return False


def embed_job_description(job_id: str, job_description: str) -> bool:
    chunk_size = 500
    chunks = [job_description[i : i + chunk_size] for i in range(0, len(job_description), chunk_size)]
    return embed_and_store(documents=chunks, collection_name="job_descriptions", metadatas=[{"job_id": job_id, "chunk_idx": i} for i in range(len(chunks))], ids=[f"job_{job_id}_chunk_{i}" for i in range(len(chunks))])
