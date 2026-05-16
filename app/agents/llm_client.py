"""Async LLM client for calling Groq API."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

# Model configuration
PRIMARY_MODEL = "llama3-70b-8192"
FALLBACK_MODEL = "mixtral-8x7b-32768"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 2.0


class RateLimitError(RuntimeError):
    """Raised when Groq returns HTTP 429 after retry attempts are exhausted."""


def _is_rate_limit_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    error_msg = str(exc).lower()
    return (
        status_code == 429
        or response_status == 429
        or "429" in error_msg
        or "rate_limit" in error_msg
        or "rate limit" in error_msg
        or "too many requests" in error_msg
    )


async def call_groq(
    prompt: str,
    system: str = "",
    max_tokens: int = 2000,
    model: Optional[str] = None,
) -> str:
    """
    Call Groq API asynchronously with retry logic and model fallback.
    
    Args:
        prompt: User prompt
        system: System prompt (optional)
        max_tokens: Maximum tokens in response
        model: Model to use (defaults to PRIMARY_MODEL)
    
    Returns:
        Generated text response
    
    Raises:
        RuntimeError: If all retries fail
    """
    if model is None:
        model = PRIMARY_MODEL
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    client = Groq(api_key=api_key)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    backoff = INITIAL_BACKOFF
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Calling Groq API (attempt {attempt + 1}/{MAX_RETRIES}) with model: {model}")
            
            # Run sync Groq call in thread pool
            response = await asyncio.to_thread(
                _call_groq_sync,
                client,
                model,
                messages,
                max_tokens,
            )
            
            logger.info(f"Groq API call succeeded with model: {model}")
            return response
        
        except Exception as e:
            last_error = e
            is_rate_limit = _is_rate_limit_error(e)
            
            if is_rate_limit:
                logger.warning("Groq rate limit on retry attempt %s/%s: %s", attempt + 1, MAX_RETRIES, e)
                
                # Try fallback model on first rate limit if using primary
                if attempt == 0 and model == PRIMARY_MODEL:
                    logger.info(f"Switching to fallback model: {FALLBACK_MODEL}")
                    model = FALLBACK_MODEL
                    backoff = INITIAL_BACKOFF  # Reset backoff for fallback model
                    continue
                
                # Otherwise, backoff and retry
                if attempt < MAX_RETRIES - 1:
                    wait_time = backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    backoff *= BACKOFF_MULTIPLIER
                    continue
                error_msg = f"Groq API rate limit exceeded after {MAX_RETRIES} retries"
                logger.error("%s: %s", error_msg, last_error)
                raise RateLimitError(error_msg) from last_error
            else:
                # For non-rate-limit errors, try fewer retries
                logger.error(f"API error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    backoff *= BACKOFF_MULTIPLIER
                    continue
    
    # All retries exhausted
    error_msg = f"Failed to call Groq API after {MAX_RETRIES} attempts: {last_error}"
    logger.error(error_msg)
    raise RuntimeError(error_msg) from last_error


def _call_groq_sync(
    client: Groq,
    model: str,
    messages: list[dict],
    max_tokens: int,
) -> str:
    """
    Synchronous wrapper for Groq API call (runs in thread pool).
    
    Args:
        client: Groq client instance
        model: Model to use
        messages: Message list
        max_tokens: Max tokens in response
    
    Returns:
        Response text
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    
    return response.choices[0].message.content
