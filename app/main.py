from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.auth.schemas import UserCreate, UserRead
from app.auth.users import auth_backend, fastapi_users
from app.config import get_settings
from app.db.base import Base, async_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup if needed
    await async_engine.dispose()


def create_app() -> FastAPI:
    # Validate configuration on startup; this will raise if config is invalid
    settings = get_settings()
    logger.info(f"Configuration loaded: environment={settings.environment}, s3_endpoint={settings.s3_endpoint_url}")

    app = FastAPI(
        title="Rozgaar AI Job Agent",
        version="1.0.0",
        lifespan=lifespan,
    )

    cors_origins = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    app.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix=f"{settings.api_v1_prefix}/auth/jwt",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix=f"{settings.api_v1_prefix}/auth",
        tags=["auth"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
