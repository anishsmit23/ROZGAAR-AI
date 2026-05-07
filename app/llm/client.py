"""
LLM Client with Groq primary + OpenAI fallback.
Supports streaming, structured output, and automatic retry logic.
"""

import logging
from typing import Any, Optional, Generator

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
# langchain_core internals differ between versions; avoid hard dependency
BaseLanguageModel = Any
BaseModel = Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client with Groq primary + OpenAI fallback."""
    
    def __init__(self, use_groq: bool = True):
        """Initialize LLM client (lazy connection)."""
        self.settings = get_settings()
        self.use_groq = use_groq
        self._groq_client = None
        self._openai_client = None
        self._clients_initialized = False
    
    def _ensure_clients_initialized(self):
        """Lazy initialization of clients."""
        if self._clients_initialized:
            return
        
        # Groq client (OpenAI-compatible)
        try:
            self._groq_client = ChatGroq(
                api_key=self.settings.groq_api_key,
                model_name=self.settings.llm_model or "llama-3.3-70b-versatile",
                temperature=self.settings.llm_temperature,
                base_url=self.settings.groq_base_url or "https://api.groq.com/openai/v1",
                timeout=30,
                max_retries=2,
            )
            logger.info(f"Groq client initialized with model: {self.settings.llm_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self._groq_client = None
        
        # OpenAI client (fallback)
        try:
            self._openai_client = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model_name="gpt-4-turbo-preview",
                temperature=self.settings.llm_temperature,
                timeout=30,
                max_retries=2,
            )
            logger.info("OpenAI fallback client initialized")
        except Exception as e:
            logger.warning(f"OpenAI fallback not available: {e}")
            self._openai_client = None
        
        self._clients_initialized = True
    
    @property
    def client(self) -> Any:
        """Get primary or fallback LLM client."""
        self._ensure_clients_initialized()
        
        if self.use_groq and self._groq_client:
            return self._groq_client
        elif self._openai_client:
            logger.warning("Falling back to OpenAI (Groq unavailable)")
            return self._openai_client
        else:
            raise RuntimeError("No LLM client available (Groq and OpenAI both failed)")
    
    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        streaming: bool = False,
    ) -> str:
        """Invoke LLM with a prompt."""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        client = self.client
        if temperature is not None:
            client = client.with_config({"temperature": temperature})
        
        response = client.invoke(messages)
        return response.content
    
    def invoke_structured(
        self,
        prompt: str,
        output_schema: type[Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        """Invoke LLM with structured JSON output."""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        client = self.client
        if temperature is not None:
            client = client.with_config({"temperature": temperature})
        
        structured_client = client.with_structured_output(output_schema)
        response = structured_client.invoke(messages)

        # Support varied structured response types: prefer `model_dump()` when available
        if hasattr(response, "model_dump"):
            try:
                return response.model_dump()
            except Exception:
                pass
        if hasattr(response, "dict"):
            try:
                return response.dict()
            except Exception:
                pass
        return response
    
    def batch_invoke(
        self,
        prompts: list[str],
        system_prompt: Optional[str] = None,
    ) -> list[str]:
        """Batch invoke LLM with multiple prompts."""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        client = self.client
        messages_list = []
        
        for prompt in prompts:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            messages_list.append(messages)
        
        responses = client.batch(messages_list)
        return [r.content for r in responses]
    
    def retry_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_attempts: int = 2,
    ) -> str:
        """Invoke with automatic fallback on failure."""
        attempts = 0
        last_error = None
        
        # Try primary (Groq)
        self._ensure_clients_initialized()
        if self._groq_client:
            try:
                self.use_groq = True
                return self.invoke(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"Groq failed: {e}")
                last_error = e
                attempts += 1
        
        # Try fallback (OpenAI)
        if self._openai_client and attempts < max_attempts:
            try:
                self.use_groq = False
                return self.invoke(prompt, system_prompt)
            except Exception as e:
                logger.error(f"OpenAI fallback failed: {e}")
                last_error = e
        
        raise RuntimeError(f"All LLM attempts failed: {last_error}")


# Global singleton instance
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client(use_groq: bool = True) -> LLMClient:
    """Get or create singleton LLM client."""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient(use_groq=use_groq)
    return _llm_client_instance
