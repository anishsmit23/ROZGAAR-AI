from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication.strategy import Strategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from jose import jwt

from app.config import get_settings
from app.db.base import async_session
from app.db.models.user import User

settings = get_settings()


async def get_user_db() -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    async with async_session() as session:
        yield SQLAlchemyUserDatabase(session, User)


class UserManager(BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.reset_password_secret
    verification_token_secret = settings.verification_secret


async def get_user_manager(user_db=Depends(get_user_db)) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


class RS256JWTStrategy(Strategy[User, UUID]):
    def __init__(self, private_key: str, public_key: str, lifetime_seconds: int) -> None:
        self.private_key = private_key
        self.public_key = public_key
        self.lifetime_seconds = lifetime_seconds

    async def read_token(self, token: str, user_manager: BaseUserManager[User, UUID]) -> User | None:
        try:
            payload = jwt.decode(token, self.public_key, algorithms=["RS256"], audience="fastapi-users:auth")
            user_id = payload.get("sub")
            if not user_id:
                return None
            return await user_manager.get(UUID(user_id))
        except Exception:
            return None

    async def write_token(self, user: User) -> str:
        now = datetime.now(tz=timezone.utc)
        expire = now + timedelta(seconds=self.lifetime_seconds)
        payload = {
            "sub": str(user.id),
            "aud": "fastapi-users:auth",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")


def get_jwt_strategy() -> RS256JWTStrategy:
    return RS256JWTStrategy(
        private_key=settings.jwt_private_key,
        public_key=settings.jwt_public_key,
        lifetime_seconds=settings.jwt_access_token_expire_minutes * 60,
    )

bearer_transport = BearerTransport(tokenUrl=f"{settings.api_v1_prefix}/auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])
