from __future__ import annotations

from uuid import UUID

from fastapi_users import schemas


class UserRead(schemas.BaseUser[UUID]):
    full_name: str | None = None
    skills: list[str] | None = None
    experience_years: int | None = None
    resume_path: str | None = None
    preferences: dict | None = None


class UserCreate(schemas.BaseUserCreate):
    full_name: str | None = None
    skills: list[str] | None = None
    experience_years: int | None = None
    resume_path: str | None = None
    preferences: dict | None = None


class UserUpdate(schemas.BaseUserUpdate):
    pass
