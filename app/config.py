from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    public_api_url: str = "http://127.0.0.1:8000"
    cors_extra_origins: str = ""

    database_url: str
    redis_url: str
    chroma_url: str
    serpapi_key: str = ""

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "raw-html"

    celery_broker_url: str
    celery_result_backend: str

    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_private_key_file: str | None = None
    jwt_public_key_file: str | None = None
    jwt_access_token_expire_minutes: int = 60
    reset_password_secret: str = "reset-password-secret"
    verification_secret: str = "verification-secret"

    groq_api_key: str | None = None
    openai_api_key: str | None = None
    groq_base_url: str | None = None
    llm_model: str | None = None
    llm_temperature: float = 0.2

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis_url

    @property
    def CHROMA_URL(self) -> str:
        return self.chroma_url

    @property
    def SERPAPI_KEY(self) -> str:
        return self.serpapi_key

    @property
    def MINIO_ENDPOINT(self) -> str:
        return self.minio_endpoint

    @property
    def MINIO_ACCESS_KEY(self) -> str:
        return self.minio_access_key

    @property
    def MINIO_SECRET_KEY(self) -> str:
        return self.minio_secret_key

    @property
    def MINIO_BUCKET(self) -> str:
        return self.minio_bucket

    def _read_secret_value(self, value: str, file_path: str | None, name: str) -> str:
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
        return self._read_secret_value(self.jwt_private_key, self.jwt_private_key_file, "JWT_PRIVATE_KEY")

    @property
    def jwt_public_key_value(self) -> str:
        return self._read_secret_value(self.jwt_public_key, self.jwt_public_key_file, "JWT_PUBLIC_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
