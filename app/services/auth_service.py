from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AuthenticationError, DuplicateResourceError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
        self.session = session

    async def register(self, req: UserRegisterRequest) -> User:
        existing = await self.user_repo.get_by_email(req.email)
        if existing:
            raise DuplicateResourceError(f"User with email '{req.email}' already exists")

        pw_hash = hash_password(req.password)
        user = await self.user_repo.create(
            email=req.email,
            password_hash=pw_hash,
            role=req.role or "user",
            is_active=True,
        )
        await self.session.commit()
        return user

    async def login(self, req: UserLoginRequest) -> Tuple[User, str, str]:
        user = await self.user_repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("User account is deactivated")

        payload = {"sub": user.id, "email": user.email, "role": user.role}
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)
        return user, access_token, refresh_token

    async def refresh(self, refresh_token_str: str) -> Tuple[str, str]:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type; refresh token required")

        user_id = payload.get("sub")
        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        new_payload = {"sub": user.id, "email": user.email, "role": user.role}
        access_token = create_access_token(new_payload)
        refresh_token = create_refresh_token(new_payload)
        return access_token, refresh_token
