from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from app.db.base import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
