"""
Application configuration using Pydantic Settings.

All configuration is driven by environment variables. Required variables must be set
or the application will fail to start. Optional variables have sensible defaults.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ==================== REQUIRED SETTINGS ====================

    database_url: str
    """PostgreSQL connection string (e.g., postgresql+asyncpg://user:pass@host:5432/db)."""

    redis_url: str
    """Redis connection string (e.g., redis://localhost:6379/0)."""

    secret_key: str
    """JWT signing secret. Must be at least 32 characters for security."""

    groq_api_key: str
    """Groq API key for LLM calls. Get from https://console.groq.com/keys."""

    # ==================== OPTIONAL SETTINGS WITH DEFAULTS ====================

    api_v1_prefix: str = "/api/v1"
    """API v1 endpoint prefix for FastAPI routes."""

    chroma_host: str = "http://chromadb:8000"
    """ChromaDB HTTP endpoint for semantic search and vector storage."""

    celery_broker_url: str = "redis://redis:6379/1"
    """Redis connection string for Celery broker (task queue)."""

    celery_result_backend: str = "redis://redis:6379/2"
    """Redis connection string for Celery result backend (task results storage)."""

    jwt_private_key: str = ""
    """JWT private key for signing tokens (RS256). Can also read from JWT_PRIVATE_KEY_FILE."""

    jwt_public_key: str = ""
    """JWT public key for verifying tokens (RS256). Can also read from JWT_PUBLIC_KEY_FILE."""

    jwt_private_key_file: str | None = None
    """Path to file containing JWT private key (alternative to JWT_PRIVATE_KEY env var)."""

    jwt_public_key_file: str | None = None
    """Path to file containing JWT public key (alternative to JWT_PUBLIC_KEY env var)."""

    jwt_access_token_expire_minutes: int = 60
    """JWT access token expiration time in minutes."""

    reset_password_secret: str = "reset-password-secret"
    """Secret for password reset token generation."""

    verification_secret: str = "verification-secret"
    """Secret for email verification token generation."""

    s3_endpoint_url: str = "http://minio:9000"
    """S3-compatible endpoint URL. For production, use Cloudflare R2: https://<account-id>.r2.cloudflarestorage.com"""

    s3_access_key_id: str = "minioadmin"
    """S3 access key ID. For R2, use your API token access key."""

    s3_secret_access_key: str = "minioadmin"
    """S3 secret access key. For R2, use your API token secret access key."""

    s3_bucket_resumes: str = "generated-resumes"
    """S3 bucket name for storing customized resumes and generated PDFs."""

    adzuna_app_id: str = ""
    """Adzuna job search API app ID. Get from https://developer.adzuna.com"""

    adzuna_app_key: str = ""
    """Adzuna job search API app key. Get from https://developer.adzuna.com"""

    serpapi_key: str = ""
    """SerpAPI key for Google Jobs search. Get from https://serpapi.com"""

    llm_model: str = "llama3-70b-8192"
    """Primary LLM model to use for resume and email generation."""

    llm_fallback_model: str = "mixtral-8x7b-32768"
    """Fallback LLM model if primary model is rate-limited."""

    llm_temperature: float = 0.7
    """Temperature for LLM sampling (0-1, lower=more deterministic, higher=more creative)."""

    groq_base_url: str = "https://api.groq.com/openai/v1"
    """Groq API base URL (defaults to official Groq endpoint)."""

    openai_api_key: str = ""
    """OpenAI API key for fallback LLM (optional, only used if Groq fails)."""

    max_jobs_per_search: int = 20
    """Maximum number of jobs to fetch per search query."""

    semantic_score_threshold: float = 0.5
    """Minimum semantic similarity score (0-1) for job ranking relevance."""

    environment: Literal["development", "production"] = "development"
    """Application environment: 'development' or 'production'."""

    # ==================== PROPERTIES ====================

    def _read_secret_value(self, value: str, file_path: str | None, name: str) -> str:
        """Read secret value from environment variable or file."""
        if file_path:
            try:
                return Path(file_path).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise RuntimeError(f"{name}_FILE could not be read: {file_path}") from exc
        normalized = value.replace("\\n", "\n").strip()
        if not normalized:
            raise RuntimeError(f"{name} or {name}_FILE must be configured")
        return normalized

    @property
    def jwt_private_key_value(self) -> str:
        """Get JWT private key from file or environment."""
        return self._read_secret_value(self.jwt_private_key, self.jwt_private_key_file, "JWT_PRIVATE_KEY")

    @property
    def jwt_public_key_value(self) -> str:
        """Get JWT public key from file or environment."""
        return self._read_secret_value(self.jwt_public_key, self.jwt_public_key_file, "JWT_PUBLIC_KEY")

    # ==================== VALIDATORS ====================

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is at least 32 characters for security."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> Settings:
        """
        Validate that all required fields are non-empty.
        In production, also validate S3 configuration.
        """
        required_fields = {
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "SECRET_KEY": self.secret_key,
            "GROQ_API_KEY": self.groq_api_key,
        }

        missing = [name for name, value in required_fields.items() if not value or not str(value).strip()]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"See .env.example for configuration details."
            )

        # Production-specific validation
        if self.environment == "production":
            if "localhost" in self.s3_endpoint_url or "minio" in self.s3_endpoint_url:
                raise ValueError(
                    f"Invalid S3_ENDPOINT_URL for production: '{self.s3_endpoint_url}'. "
                    f"Production must use a cloud S3 endpoint (e.g., Cloudflare R2). "
                    f"For local dev, use environment=development or S3_ENDPOINT_URL=http://minio:9000"
                )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Load and cache application settings.
    
    Settings are loaded from environment variables and validated on first call.
    If validation fails, the application will raise an exception immediately.
    
    Returns:
        Validated Settings instance (cached for subsequent calls)
    
    Raises:
        ValidationError: If any required settings are missing or invalid
    """
    return Settings()
