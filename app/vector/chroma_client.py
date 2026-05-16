"""ChromaDB vector store for resume embeddings and job ranking."""
from __future__ import annotations

import logging
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer, util

from app.config import get_settings

logger = logging.getLogger(__name__)

# Model for embedding
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 512  # Target tokens per chunk (~2048 characters)
CHUNK_OVERLAP = 64  # Overlap tokens (~256 characters)
MIN_SCORE = 0.5  # Minimum cosine similarity for relevance

# Rough conversion: 1 token ≈ 4 characters
CHARS_PER_TOKEN = 4
CHUNK_SIZE_CHARS = CHUNK_SIZE * CHARS_PER_TOKEN  # ~2048 chars
OVERLAP_CHARS = CHUNK_OVERLAP * CHARS_PER_TOKEN  # ~256 chars


def _resume_collection_name(user_id: str) -> str:
    return f"resumes_{user_id}"


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Characters per chunk
        overlap: Characters of overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        
        # Move start position, accounting for overlap
        start = end - overlap
        
        # Avoid infinite loop on very small text
        if start >= len(text):
            break
    
    return chunks


class VectorStore:
    """Vector store for resume embeddings and job ranking using ChromaDB."""
    
    def __init__(self, chroma_url: str | None = None):
        """
        Initialize ChromaDB client and load embedding model.
        
        Args:
            chroma_url: ChromaDB server URL (defaults to settings.chroma_host)
        """
        if not chroma_url:
            settings = get_settings()
            chroma_url = settings.chroma_host
        
        self.chroma_url = chroma_url
        
        # Parse host and port from URL
        url_parts = chroma_url.replace("http://", "").split(":")
        host = url_parts[0] if url_parts else "chromadb"
        port = int(url_parts[1]) if len(url_parts) > 1 else 8000
        
        self.client = chromadb.HttpClient(host=host, port=port)
        
        # Load sentence-transformer model
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        logger.info(f"VectorStore initialized with ChromaDB at {chroma_url}")
    
    def embed_and_store_resume(self, user_id: str, resume_text: str) -> None:
        """
        Chunk resume text, embed it, and store in ChromaDB.
        
        Args:
            user_id: User UUID
            resume_text: Full resume text
        """
        if not resume_text or not resume_text.strip():
            logger.warning(f"Empty resume text for user {user_id}")
            return
        
        try:
            # Chunk the resume
            chunks = _chunk_text(resume_text)
            logger.info(f"Chunked resume for user {user_id} into {len(chunks)} chunks")
            
            # Get or create a per-user collection for resumes.
            collection = self.client.get_or_create_collection(
                name=_resume_collection_name(user_id),
                metadata={"hnsw:space": "cosine"}
            )
            
            # Embed chunks
            embeddings = self.embedding_model.encode(chunks, convert_to_tensor=False)
            
            # Prepare documents and IDs
            ids = [f"{user_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"user_id": user_id, "chunk_index": i} for i in range(len(chunks))]
            
            # Upsert into collection
            collection.upsert(
                documents=chunks,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas,
            )
            
            logger.info(f"Stored {len(chunks)} resume chunks for user {user_id}")
        
        except Exception as e:
            logger.error(f"Error storing resume for user {user_id}: {e}", exc_info=True)
            raise
    
    def score_job(self, user_id: str, job_description: str) -> float:
        """
        Score a job description against a user's resume using cosine similarity.
        
        Args:
            user_id: User UUID
            job_description: Job posting description/requirements
        
        Returns:
            Max cosine similarity score (0.0 to 1.0) or 0.0 if no resume found
        """
        if not job_description or not job_description.strip():
            logger.warning(f"Empty job description for user {user_id}")
            return 0.0
        
        try:
            collection = self.client.get_or_create_collection(
                name=_resume_collection_name(user_id),
                metadata={"hnsw:space": "cosine"}
            )
            
            # Check if user has any resume chunks
            results = collection.get(
                where={"user_id": user_id},
                limit=1,
            )
            
            if not results or not results.get("documents"):
                logger.debug(f"No resume found for user {user_id}")
                return 0.0
            
            # Embed job description
            job_embedding = self.embedding_model.encode(job_description, convert_to_tensor=True)
            
            # Query ChromaDB for similar resume chunks
            query_results = collection.query(
                query_embeddings=[job_embedding.tolist()],
                where={"user_id": user_id},
                n_results=5,  # Get top 5 chunks
            )
            
            # Return max distance (ChromaDB returns distances, we convert to similarity)
            if query_results and query_results.get("distances"):
                distances = query_results["distances"][0]
                # For cosine distance, similarity = 1 - distance
                similarities = [max(0.0, 1.0 - d) for d in distances]
                max_score = max(similarities) if similarities else 0.0
                logger.debug(f"Job score for user {user_id}: {max_score:.3f}")
                return max_score
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Error scoring job for user {user_id}: {e}", exc_info=True)
            return 0.0
    
    def rank_jobs(self, user_id: str, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Score and rank jobs by semantic similarity to user's resume.
        
        Args:
            user_id: User UUID
            jobs: List of job dicts (each with 'description' key)
        
        Returns:
            List of jobs with added 'semantic_score' key, sorted by score descending
        """
        try:
            # Score each job
            for job in jobs:
                description = job.get("description", "")
                score = self.score_job(user_id, description)
                job["semantic_score"] = score
            
            # Sort by semantic_score descending
            ranked = sorted(jobs, key=lambda j: j.get("semantic_score", 0.0), reverse=True)
            
            logger.info(f"Ranked {len(ranked)} jobs for user {user_id}")
            return ranked
        
        except Exception as e:
            logger.error(f"Error ranking jobs for user {user_id}: {e}", exc_info=True)
            # Return jobs as-is without scores on error
            return jobs
